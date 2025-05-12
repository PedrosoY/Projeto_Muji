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
        """
        Percorre cada string, identifica frequência (ex: 20GHz)
        e pesos (i=10, j=5, r=3) em qualquer ordem.
        """
        for item in itens:
            texto = item.strip().lower()
            # tenta extrair frequência: número + unidade
            m = re.match(r'([\d\.]+)\s*([kmg]?hz)', texto)
            if m:
                valor, unidade = m.groups()
                self.clock_hz = float(valor) * self._fatores[unidade]
                continue
            # tenta extrair peso: i=valor, j=valor, r=valor
            m2 = re.match(r'(i|j|r)\s*=\s*(\d+)', texto)
            if m2:
                tipo, val = m2.groups()
                self.pesos[tipo.upper()] = int(val)
                continue

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
        """
        Lê arquivo ignorando comentários e vazios.
        offset_linhas: linha a partir da qual começam as instruções.
        """
        with open(caminho, 'r') as f:
            for idx, linha in enumerate(f):
                if idx < offset_linhas:
                    continue
                txt = linha.strip()
                if not txt or txt.startswith('#'):
                    continue
                self.instrucoes.append(txt)
    def instantanea(self) -> list[tuple]:
        """
        Retorna lista de:
        (endereco_byte, codigo32hex, textoInstrucao, opcode)
        """
        tabela = []
        for idx, instr in enumerate(self.instrucoes):
            endereco = idx * 4
            codigo32 = hex(abs(hash(instr)) & 0xFFFFFFFF)
            opcode = instr.split()[0]
            tabela.append((endereco, codigo32, instr, opcode))
        return tabela
    def ler_instrucao(self, indice: int) -> str | None:
        """Retorna instrução pelo índice (PC//4) ou None."""
        if 0 <= indice < len(self.instrucoes):
            return self.instrucoes[indice]
        return None

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
    """Decodifica texto e classifica em tipo R, I ou J."""
    def __init__(self, texto: str):
        self.texto = texto
        partes = texto.replace(',', '').split()
        self.op = partes[0]
        self.args = partes[1:]
        if self.op in ('j','jal'):
            self.tipo = 'J'
        elif self.op in ('add','sub','and','or'):
            self.tipo = 'R'
        else:
            self.tipo = 'I'
        self.codigo32 = hex(abs(hash(texto)) & 0xFFFFFFFF)

# --------------------------------------------------------------------------------
# Memoria do computador
# --------------------------------------------------------------------------------

# Adicionar o bloco de Memoria do computador, para exibir se foi salvo as informações
    # Codigo da linha da memoria do Computador (como 0xasd50842)
    # O Valor da memoria em Hexadecimal
    # Valores armazenados nela em Decimal (pode ser palavras, numeros, etc)
        # Byte = 8 bits
        # Halfword = 2 bytes
        # Word = 4 bytes
        # Um caractere ocupa 1 byte na memória
        # Um inteiro ocupa 1 word(4 bytes) na memória
            # Formatações: Números são representados normalmente. Ex: 4
            # Caracteres ficam entre aspas simples. Ex: a Strings ficam entre
            # aspas duplas. Ex: palavra


class MemoriaComputador:
    """
    Simula a memória de dados do computador:
     - endereços de 0 a N bytes
     - suporta operações de byte (1B), halfword (2B) e word (4B)
     - armazena valores inteiros ou caracteres/string
     - snapshot de conteúdo para exibição
    """
    def __init__(self, tamanho_bytes: int = 1024):
        # inicializa memória com zeros
        self.tamanho = tamanho_bytes
        self.mem = bytearray(tamanho_bytes)
        # mapa de endereços escritos: addr -> (size, tipo)
        self._mapa = {}

    def escrever(self, endereco: int, valor, size: int):
        """
        Escreve valor na memória:
        - endereco: offset em bytes
        - valor: int ou str (um caractere ou string)
        - size: número de bytes: 1, 2 ou 4
        """
        if endereco < 0 or endereco + size > self.tamanho:
            raise ValueError(f"Endereço {endereco} fora do intervalo de memória")
        # converte valor para bytes little-endian
        if isinstance(valor, str):
            # string ou caractere
            b = valor.encode('ascii')
            if len(b) != size:
                raise ValueError(f"Tamanho da string {len(b)} diferente de {size}")
        else:
            # inteiro
            b = valor.to_bytes(size, byteorder='little', signed=True)
        self.mem[endereco:endereco+size] = b
        self._mapa[endereco] = (size, valor)

    def ler(self, endereco: int, size: int):
        """
        Lê valor da memória:
        - endereco: offset em bytes
        - size: número de bytes a ler
        Retorna int ou string (se foi escrito como caractere/string)
        """
        if endereco < 0 or endereco + size > self.tamanho:
            raise ValueError(f"Endereço {endereco} fora do intervalo de memória")
        b = self.mem[endereco:endereco+size]
        # se endereço mapeado para string, retorna string
        if endereco in self._mapa and isinstance(self._mapa[endereco][1], str):
            return b.decode('ascii')
        # senão retorna inteiro
        return int.from_bytes(b, byteorder='little', signed=True)

    def instantanea(self) -> list[tuple]:
        """
        Retorna lista de tuplas para exibição:
        (EndereçoHex, Tipo, ValorHex, ValorDec)
        """
        rows = []
        for addr in sorted(self._mapa):
            size, valor_original = self._mapa[addr]
            tipo = {1: 'Byte', 2: 'Halfword', 4: 'Word'}.get(size, f'{size}B')
            # lê bytes atuais
            b = self.mem[addr:addr+size]
            val_int = int.from_bytes(b, byteorder='little', signed=True)
            hex_repr = '"' + valor_original + '"' if isinstance(valor_original, str) else hex(val_int)
            rows.append((f"0x{addr:08X}", tipo, hex_repr, val_int))
        return rows

# --------------------------------------------------------------------------------
# Simulador MIPS completo
# --------------------------------------------------------------------------------
class SimuladorMIPS:
    """
    Simula ciclo a ciclo:
     - lê config_CPU na 1ª linha do arquivo
     - calcula T = 1/clock_hz
     - para cada instrução acumula tempo (peso×T)
     - exibe estado de registradores e memória (.text)
    """
    def __init__(self, caminho_arquivo: Path):
        # lê todas as linhas para extrair config e instruções
        linhas = caminho_arquivo.read_text().splitlines()
        # encontra linha config_CPU = [...]
        cfg_line = next(l for l in linhas if l.lower().startswith('config_cpu'))
        # extrai conteúdo dentro de colchetes
        conteudo = re.search(r'\[(.*)\]', cfg_line).group(1)
        itens = [i.strip() for i in conteudo.split(',')]
        # instancia configuração
        self.config = ConfiguracaoCPU(itens)
        # prepara memória de programa a partir da 2ª linha (offset 1)
        self.memoria = MemoriaPrograma()
        self.memoria.carregar(caminho_arquivo, offset_linhas=1)
        # inicializa registradores, PC, relógio e tempo acumulado
        self.registradores = BancoDeRegistradores()
        self.pc = 0
        self.relogio = Relogio()
        self.tempo_acumulado = 0.0

    def executar_passo(self) -> bool:
        """
        Executa uma instrução:
         - decodifica
         - incrementa ciclo e tempo
         - executa li e add (exemplos)
         - exibe estado
        Retorna False quando não há mais instruções.
        """
        idx = self.pc // 4
        txt = self.memoria.ler_instrucao(idx)
        if txt is None:
            return False
        inst = Instrucao(txt)
        # incrementa ciclo
        self.relogio.tick()
        # adiciona tempo: peso do tipo × T
        peso = self.config.pesos[inst.tipo]
        self.tempo_acumulado += peso * self.config.T

        # execução simples de exemplo
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
        # ... outros opcodes aqui

        # exibe antes de PC avançar
        self.exibir_estado(inst)
        self.pc += 4
        return True

    def exibir_estado(self, inst: Instrucao):
        """Imprime cabeçalho, registradores e memória de programa (.text)."""
        # cabeçalho com tempo formatado e ciclos
        header = [
            ['Tempo', formatar_tempo(self.tempo_acumulado)],
            ['Ciclos', self.relogio.ciclo],
            ['PC', f"0x{self.pc:08X}"],
            ['Tipo', inst.tipo],
            ['Instr', inst.texto],
        ]
        print(tabulate(header, tablefmt='plain'))

        # tabela de registradores
        print('\nRegistradores:')
        regs = self.registradores.instantanea()
        print(tabulate(regs, headers=['Num','Nome','Hex','Dec']))

        # tabela de memória de programa, destacando PC atual
        print('\nMemória de Programa (.text):')
        rows = []
        for end, cod32, txt, opc in self.memoria.instantanea():
            marcador = '>>' if end == self.pc else '  '
            rows.append((marcador, f"0x{end:08X}", cod32, txt, opc))
        print(tabulate(rows, headers=['','Endereço','Cod32','Instr','Op']))
        print('\n' + '='*60 + '\n')

    def exibir_estado_final(self):
        """Mostra registradores, memória e tempo total ao final da simulação."""
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


# Adicionar o bloco de Memoria do computador, para exibir se foi salvo as informações
    # Codigo ADD li
    # O Valor da memoria em Hexadecimal
    # Linha do PC
    # Valores armazenados nela

# Exibir sempre uma tabela a cada linha dinamicamente com nome, numero, valor, registrador, memoria

# Memoria RAM
    # Endereço na memoria
    # Codigo do programa convertido
    # A linha atual
    # Registradores

# Registradores 32
    # O que cada registrador faz

# Interação com clock onde cada click é 1 ciclo de clock


# Sempre mostrar o Tempo de execução (incremental)
# Programing Counter (PC)
# Tipo da Instrução
# Instrução Atual = 32 Bits = Hexadecimal

# Para cada tipo de instrução tem seu conjunto, ou seja, se for do tipo J, são todas de Jump da tabela