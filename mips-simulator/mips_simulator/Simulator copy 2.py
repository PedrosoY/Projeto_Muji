from pathlib import Path
import re
from tabulate import tabulate

# --------------------------------------------------------------------------------
# Função auxiliar para formatar tempos em unidades legíveis
# --------------------------------------------------------------------------------
def formatar_tempo(segundos: float) -> str:
    """
    Converte um valor em segundos para a unidade mais apropriada:
    s, ms, µs ou ns, e retorna string formatada.
    """
    if segundos >= 1:
        return f"{segundos:.6f} s"
    ms = segundos * 1e3
    if ms >= 1:
        return f"{ms:.3f} ms"
    us = segundos * 1e6
    if us >= 1:
        return f"{us:.3f} µs"
    ns = segundos * 1e9
    return f"{ns:.3f} ns"

# --------------------------------------------------------------------------------
# Classe de configuração da CPU: parseia clock e pesos de instruções
# --------------------------------------------------------------------------------
class ConfiguracaoCPU:
    """
    Lê lista de itens como ['20GHz','i=10','j=5','r=1'] e extrai:
     - clock_hz: frequência em Hz (float)
     - pesos: dict {'I': int, 'J': int, 'R': int}
    """
    def __init__(self, itens: list[str]):
        # fatores de conversão para Hz
        self._fatores = {'hz':1, 'khz':1e3, 'mhz':1e6, 'ghz':1e9}
        self.clock_hz = None
        # pesos padrão 1 ciclo
        self.pesos = {'I':1, 'J':1, 'R':1}
        self._parse_itens(itens)
        # tempo de um ciclo T = 1 / clock
        self.T = 1.0 / self.clock_hz

    def _parse_itens(self, itens: list[str]):
        for item in itens:
            texto = item.strip().lower()
            m = re.match(r'([\d\.]+)\s*([kmg]?hz)', texto)
            if m:
                valor, unidade = m.groups()
                self.clock_hz = float(valor) * self._fatores[unidade]
                continue
            m2 = re.match(r'(i|j|r)\s*=\s*(\d+)', texto)
            if m2:
                tipo, val = m2.groups()
                self.pesos[tipo.upper()] = int(val)

# --------------------------------------------------------------------------------
# Banco de registradores MIPS
# --------------------------------------------------------------------------------
class BancoDeRegistradores:
    """32 registradores de 32 bits, de $zero a $ra."""
    def __init__(self):
        nomes = [
            'zero','at','v0','v1','a0','a1','a2','a3',
            't0','t1','t2','t3','t4','t5','t6','t7',
            's0','s1','s2','s3','s4','s5','s6','s7',
            't8','t9','k0','k1','gp','sp','fp','ra'
        ]
        self.regs = {f"${nome}": 0 for nome in nomes}

    def escrever(self, registrador: str, valor: int):
        """Grava valor inteiro de 32 bits; $zero permanece 0."""
        if registrador != '$zero':
            self.regs[registrador] = valor

    def ler(self, registrador: str) -> int:
        """Retorna valor inteiro de um registrador."""
        return self.regs.get(registrador, 0)

    def instantanea(self) -> list[tuple]:
        """
        Gera snapshot atual:
        lista de tuplas (Num, Nome, ValorHex, ValorDec)
        """
        tabela = []
        for idx, nome in enumerate(self.regs):
            v = self.regs[nome]
            tabela.append((idx, nome, hex(v), v))
        return tabela

# --------------------------------------------------------------------------------
# Memória de programa (.text): cada instrução ocupa 32 bits (4 bytes)
# --------------------------------------------------------------------------------
class MemoriaPrograma:
    """Armazena lista de instruções de 4 em 4 bytes."""
    def __init__(self):
        self.instrucoes: list[str] = []

    def carregar(self, caminho: Path, offset_linhas: int = 0):
        with open(caminho, 'r') as f:
            for idx, linha in enumerate(f):
                if idx < offset_linhas:
                    continue
                txt = linha.strip()
                if not txt or txt.startswith('#'):
                    continue
                self.instrucoes.append(txt)

    def instantanea(self) -> list[tuple]:
        tabela = []
        for idx, instr in enumerate(self.instrucoes):
            endereco = idx * 4
            codigo32 = hex(abs(hash(instr)) & 0xFFFFFFFF)
            opcode = instr.split()[0]
            tabela.append((endereco, codigo32, instr, opcode))
        return tabela

    def ler_instrucao(self, indice: int) -> str | None:
        if 0 <= indice < len(self.instrucoes):
            return self.instrucoes[indice]
        return None

# --------------------------------------------------------------------------------
# Memória de dados (RAM)
# --------------------------------------------------------------------------------
class MemoriaComputador:
    """
    Simula a memória de dados do computador:
     - endereços de 0 a N bytes
     - suporta operações de byte (1B), halfword (2B) e word (4B)
     - armazena valores inteiros ou caracteres/string
    """
    def __init__(self, tamanho_bytes: int = 1024):
        self.tamanho = tamanho_bytes
        self.mem = bytearray(tamanho_bytes)
        self._mapa = {}  # addr -> (size, valor_original)

    def escrever(self, endereco: int, valor, size: int):
        if endereco < 0 or endereco + size > self.tamanho:
            raise ValueError(f"Endereço {endereco} fora do intervalo de memória")
        if isinstance(valor, str):
            b = valor.encode('ascii')
            if len(b) != size:
                raise ValueError(f"Tamanho da string {len(b)} diferente de {size}")
        else:
            b = valor.to_bytes(size, byteorder='little', signed=True)
        self.mem[endereco:endereco+size] = b
        self._mapa[endereco] = (size, valor)

    def ler(self, endereco: int, size: int):
        if endereco < 0 or endereco + size > self.tamanho:
            raise ValueError(f"Endereço {endereco} fora do intervalo de memória")
        b = self.mem[endereco:endereco+size]
        if endereco in self._mapa and isinstance(self._mapa[endereco][1], str):
            return b.decode('ascii')
        return int.from_bytes(b, byteorder='little', signed=True)

    def instantanea(self) -> list[tuple]:
        rows = []
        for addr in sorted(self._mapa):
            size, original = self._mapa[addr]
            tipo = {1:'Byte',2:'Halfword',4:'Word'}.get(size, f'{size}B')
            b = self.mem[addr:addr+size]
            val_int = int.from_bytes(b, byteorder='little', signed=True)
            hex_repr = f"\"{original}\"" if isinstance(original, str) else hex(val_int)
            rows.append((f"0x{addr:08X}", tipo, hex_repr, val_int))
        return rows

# --------------------------------------------------------------------------------
# Relógio de ciclos
# --------------------------------------------------------------------------------
class Relogio:
    """Conta quantos ciclos já se passaram."""
    def __init__(self):
        self.ciclo = 0
    def tick(self):
        self.ciclo += 1

# --------------------------------------------------------------------------------
# Decodificação básica de instrução
# --------------------------------------------------------------------------------
class Instrucao:
    """Decodifica texto e classifica em tipo R, I ou J, e guarda texto original."""
    def __init__(self, texto: str):
        self.texto = texto
        texto_normal = texto.replace(',', '').strip()
        partes = texto_normal.split()
        self.op = partes[0].lower()
        self.args = partes[1:]
        if self.op in ('j','jal'):
            self.tipo = 'J'
        elif self.op in ('add','sub','and','or'):
            self.tipo = 'R'
        else:
            self.tipo = 'I'
        self.codigo32 = hex(abs(hash(texto)) & 0xFFFFFFFF)

# --------------------------------------------------------------------------------
# Simulador MIPS completo
# --------------------------------------------------------------------------------
class SimuladorMIPS:
    """
    Simula ciclo a ciclo:
     - lê config_CPU na 1ª linha do arquivo
     - calcula T = 1/clock_hz
     - para cada instrução acumula tempo (peso×T)
     - exibe estado de registradores, memórias (.text e .data)
    """
    def __init__(self, caminho_arquivo: Path):
        linhas = caminho_arquivo.read_text().splitlines()
        cfg_line = next(l for l in linhas if l.lower().startswith('config_cpu'))
        conteudo = re.search(r'\[(.*)\]', cfg_line).group(1)
        itens = [i.strip() for i in conteudo.split(',')]
        self.config = ConfiguracaoCPU(itens)
        self.memoria = MemoriaPrograma()
        self.memoria.carregar(caminho_arquivo, offset_linhas=1)
        self.memoria_dados = MemoriaComputador(tamanho_bytes=1024)
        self.registradores = BancoDeRegistradores()
        self.pc = 0
        self.relogio = Relogio()
        self.tempo_acumulado = 0.0

    def executar_passo(self) -> bool:
        idx = self.pc // 4
        txt = self.memoria.ler_instrucao(idx)
        if txt is None:
            return False
        inst = Instrucao(txt)
        self.relogio.tick()
        peso = self.config.pesos[inst.tipo]
        self.tempo_acumulado += peso * self.config.T

        if inst.op == 'li':
            rd, val = inst.args
            if val.startswith("'") and val.endswith("'"):
                v = ord(val[1:-1])
            else:
                v = int(val, 0)
            self.registradores.escrever(rd, v)

        elif inst.op == 'add':
            rd, r1, r2 = inst.args
            soma = self.registradores.ler(r1) + self.registradores.ler(r2)
            self.registradores.escrever(rd, soma)

        elif inst.op == 'sw':
            rt, off_base = inst.args
            m = re.match(r'(-?0x[0-9a-f]+|-?\d+)\((\$[a-z0-9]+)\)', off_base, re.IGNORECASE)
            if not m:
                raise ValueError(f"Formato inválido de sw: {off_base}")
            offset_str, base = m.groups()
            endereco = self.registradores.ler(base) + int(offset_str, 0)
            valor = self.registradores.ler(rt)
            self.memoria_dados.escrever(endereco, valor, size=4)

        elif inst.op == 'sb':
            rt, off_base = inst.args
            m = re.match(r'(-?0x[0-9a-f]+|-?\d+)\((\$[a-z0-9]+)\)', off_base, re.IGNORECASE)
            if not m:
                raise ValueError(f"Formato inválido de sb: {off_base}")
            offset_str, base = m.groups()
            endereco = self.registradores.ler(base) + int(offset_str, 0)
            valor = self.registradores.ler(rt) & 0xFF
            self.memoria_dados.escrever(endereco, valor, size=1)

        self.exibir_estado(inst)
        self.pc += 4
        return True

    def exibir_estado(self, inst: Instrucao):
        header = [
            ['Tempo', formatar_tempo(self.tempo_acumulado)],
            ['Ciclos', self.relogio.ciclo],
            ['PC', f"0x{self.pc:08X}"],
            ['Tipo', inst.tipo],
            ['Instr', inst.texto],
        ]
        print(tabulate(header, tablefmt='plain'))

        print('\nRegistradores:')
        print(tabulate(
            self.registradores.instantanea(),
            headers=['Num','Nome','Hex','Dec']
        ))

        print('\nMemória de Programa (.text):')
        rows_text = []
        for end, cod32, txt_instr, opc in self.memoria.instantanea():
            marcador = '>>' if end == self.pc else '  '
            rows_text.append((marcador, f"0x{end:08X}", cod32, txt_instr, opc))
        print(tabulate(rows_text, headers=['','Endereço','Cod32','Instr','Op']))

        print('\nMemória de Dados (.data):')
        print(tabulate(
            self.memoria_dados.instantanea(),
            headers=['Endereço','Tipo','Hex','Dec']
        ))

        print('\n' + '='*60 + '\n')

    def exibir_estado_final(self):
        print('=== Estado Final dos Registradores ===')
        print(tabulate(
            self.registradores.instantanea(),
            headers=['Num','Nome','Hex','Dec']
        ))
        print('\n=== Estado Final da Memória (.text) ===')
        print(tabulate(
            [(f"0x{e:08X}", c32, t, o) for e,c32,t,o in self.memoria.instantanea()],
            headers=['Endereço','Cod32','Instr','Op']
        ))
        print('\n=== Estado Final da Memória de Dados (.data) ===')
        print(tabulate(
            self.memoria_dados.instantanea(),
            headers=['Endereço','Tipo','Hex','Dec']
        ))
        print(f"\nTempo total de execução: {formatar_tempo(self.tempo_acumulado)}")


# --------------------------------------------------------------------------------
# Execução principal
# --------------------------------------------------------------------------------
if __name__ == '__main__':
    caminho = Path(__file__).parent / 'codigo_executavel.txt'
    sim = SimuladorMIPS(caminho)
    print('Simulador MIPS Iniciado. Enter para próximo passo, Ctrl+C para encerrar.\n')
    try:
        while sim.executar_passo():
            input()
    except KeyboardInterrupt:
        print('\nSimulação interrompida pelo usuário.\n')
    finally:
        sim.exibir_estado_final()