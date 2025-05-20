from pathlib import Path
import re
from tabulate import tabulate
import string

# --------------------------------------------------------------------------------
# Função auxiliar para formatar tempos em unidades legíveis
# --------------------------------------------------------------------------------
def formatar_tempo(segundos: float) -> str:
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
# Classe de configuração da CPU
# --------------------------------------------------------------------------------
class ConfiguracaoCPU:
    def __init__(self, itens: list[str]):
        self._fatores = {'hz':1, 'khz':1e3, 'mhz':1e6, 'ghz':1e9}
        self.clock_hz = None
        self.pesos = {'I':1, 'J':1, 'R':1}
        self._parse_itens(itens)
        self.T = 1.0 / self.clock_hz

    def _parse_itens(self, itens: list[str]):
        for item in itens:
            txt = item.strip().lower()
            m = re.match(r'([\d\.]+)\s*([kmg]?hz)', txt)
            if m:
                val, uni = m.groups()
                self.clock_hz = float(val) * self._fatores[uni]
                continue
            m2 = re.match(r'(i|j|r)\s*=\s*(\d+)', txt)
            if m2:
                tip, v = m2.groups()
                self.pesos[tip.upper()] = int(v)

# --------------------------------------------------------------------------------
# Banco de registradores MIPS
# --------------------------------------------------------------------------------
class BancoDeRegistradores:
    def __init__(self):
        nomes = [
            'zero','at','v0','v1','a0','a1','a2','a3',
            't0','t1','t2','t3','t4','t5','t6','t7',
            's0','s1','s2','s3','s4','s5','s6','s7',
            't8','t9','k0','k1','gp','sp','fp','ra'
        ]
        self.regs = {f"${n}":0 for n in nomes}

    def escrever(self, reg: str, val: int):
        if reg != '$zero':
            self.regs[reg] = val

    def ler(self, reg: str) -> int:
        return self.regs.get(reg, 0)

    def instantanea(self) -> list[tuple]:
        tabela = []
        for idx, nome in enumerate(self.regs):
            v = self.regs[nome]
            tabela.append((idx, nome, hex(v), v))
        return tabela

# --------------------------------------------------------------------------------
# Memória de programa (.text)
# --------------------------------------------------------------------------------
class MemoriaPrograma:
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
            end = idx * 4
            c32 = hex(abs(hash(instr)) & 0xFFFFFFFF)
            op = instr.split()[0]
            tabela.append((end, c32, instr, op))
        return tabela

    def ler_instrucao(self, idx: int) -> str | None:
        if 0 <= idx < len(self.instrucoes):
            return self.instrucoes[idx]
        return None

# --------------------------------------------------------------------------------
# Memória de dados (RAM) com detecção de strings
# --------------------------------------------------------------------------------
class MemoriaComputador:
    def __init__(self, tamanho_bytes: int = 1024):
        self.tamanho = tamanho_bytes
        self.mem = bytearray(tamanho_bytes)
        self._mapa: dict[int, tuple[int, object]] = {}

    def escrever(self, endereco: int, valor, size: int):
        if endereco < 0 or endereco + size > self.tamanho:
            raise ValueError(f"Endereço {endereco} fora do intervalo")
        if isinstance(valor, str):
            b = valor.encode('ascii')
            if len(b) != size:
                raise ValueError("String com tamanho diferente de size")
        else:
            b = int(valor).to_bytes(size, 'little', signed=True)
        self.mem[endereco:endereco+size] = b
        self._mapa[endereco] = (size, valor)

    def ler(self, endereco: int, size: int):
        if endereco < 0 or endereco + size > self.tamanho:
            raise ValueError(f"Endereço {endereco} fora do intervalo")
        b = self.mem[endereco:endereco+size]
        if endereco in self._mapa and isinstance(self._mapa[endereco][1], str):
            return b.decode('ascii')
        return int.from_bytes(b, 'little', signed=True)

    def instantanea(self) -> list[tuple]:
        rows = []
        visited = set()
        addrs = sorted(self._mapa)
        i = 0
        while i < len(addrs):
            addr = addrs[i]
            if addr in visited:
                i += 1
                continue
            size, orig = self._mapa[addr]
            if size == 1:
                seq = []
                j = addr
                while j in self._mapa and self._mapa[j][0] == 1:
                    byte = self.mem[j]
                    c = chr(byte)
                    if c in string.printable and c != '\x00':
                        seq.append(c)
                        visited.add(j)
                        j += 1
                    else:
                        break
                if len(seq) > 1:
                    txt = ''.join(seq)
                    rows.append((f"0x{addr:08X}", 'String', repr(txt), None))
                    # pular endereços agrupados
                    while i < len(addrs) and addrs[i] < j:
                        i += 1
                    continue
            # caso padrão
            b = self.mem[addr:addr+size]
            val_int = int.from_bytes(b, 'little', signed=True)
            hex_repr = f"\"{orig}\"" if isinstance(orig, str) else hex(val_int)
            tipo = {1:'Byte',2:'Halfword',4:'Word'}.get(size, f'{size}B')
            rows.append((f"0x{addr:08X}", tipo, hex_repr, val_int))
            visited.add(addr)
            i += 1
        return rows

# --------------------------------------------------------------------------------
# Relógio de ciclos
# --------------------------------------------------------------------------------
class Relogio:
    def __init__(self):
        self.ciclo = 0
    def tick(self):
        self.ciclo += 1

# --------------------------------------------------------------------------------
# Decodificação de instrução
# --------------------------------------------------------------------------------
class Instrucao:
    def __init__(self, texto: str):
        self.texto = texto
        txt_norm = texto.replace(',', '').strip()
        partes = txt_norm.split()
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
    def __init__(self, caminho_arquivo: Path):
        linhas = caminho_arquivo.read_text().splitlines()
        cfg_line = next(l for l in linhas if l.lower().startswith('config_cpu'))
        conteudo = re.search(r'\[(.*)\]', cfg_line).group(1)
        itens = [i.strip() for i in conteudo.split(',')]
        self.config = ConfiguracaoCPU(itens)

        self.memoria = MemoriaPrograma()
        # pula apenas a linha de config_cpu
        self.memoria.carregar(caminho_arquivo, offset_linhas=1)

        self.memoria_dados = MemoriaComputador(1024)
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
        peso = self.config.pesos.get(inst.tipo, 1)
        self.tempo_acumulado += peso * self.config.T

        # --- instruções ---
        if inst.op == 'li':
            rd = inst.args[0]
            val = inst.args[1]
            if val.startswith("'") and val.endswith("'"):
                v = ord(val[1:-1])
            else:
                v = int(val, 0)
            self.registradores.escrever(rd, v)

        elif inst.op == 'la':
            rd = inst.args[0]
            addr = int(inst.args[1], 0)
            self.registradores.escrever(rd, addr)

        elif inst.op == 'add':
            rd, r1, r2 = inst.args
            soma = self.registradores.ler(r1) + self.registradores.ler(r2)
            self.registradores.escrever(rd, soma)

        elif inst.op == 'sw':
            rt, offb = inst.args
            m = re.match(r'(-?0x[0-9a-f]+|-?\d+)\((\$[a-z0-9]+)\)', offb, re.IGNORECASE)
            if not m:
                raise ValueError(f"sw formato inválido: {offb}")
            off, base = m.groups()
            end = self.registradores.ler(base) + int(off, 0)
            v = self.registradores.ler(rt)
            self.memoria_dados.escrever(end, v, 4)

        elif inst.op == 'sb':
            rt, offb = inst.args
            m = re.match(r'(-?0x[0-9a-f]+|-?\d+)\((\$[a-z0-9]+)\)', offb, re.IGNORECASE)
            if not m:
                raise ValueError(f"sb formato inválido: {offb}")
            off, base = m.groups()
            end = self.registradores.ler(base) + int(off, 0)
            v = self.registradores.ler(rt) & 0xFF
            self.memoria_dados.escrever(end, v, 1)

        # exibe estado
        self.exibir_estado(inst)
        self.pc += 4
        return True

    def exibir_estado(self, inst: Instrucao):
        header = [
            ['Tempo',   formatar_tempo(self.tempo_acumulado)],
            ['Ciclos',  self.relogio.ciclo],
            ['PC',      f"0x{self.pc:08X}"],
            ['Tipo',    inst.tipo],
            ['Instr',   inst.texto],
        ]
        print(tabulate(header, tablefmt='plain'))

        print('\nRegistradores:')
        print(tabulate(
            self.registradores.instantanea(),
            headers=['Num','Nome','Hex','Dec']
        ))

        print('\nMemória de Programa (.text):')
        rows = []
        for end, c32, txt, opc in self.memoria.instantanea():
            marc = '>>' if end == self.pc else '  '
            rows.append((marc, f"0x{end:08X}", c32, txt, opc))
        print(tabulate(rows, headers=['','Endereço','Cod32','Instr','Op']))

        print('\nMemória de Dados (.data):')
        print(tabulate(
            self.memoria_dados.instantanea(),
            headers=['Endereço','Tipo','Hex','Dec']
        ))
        print('\n' + '='*60 + '\n')

    def exibir_estado_final(self):
        print('=== Estado Final dos Registradores ===')
        print(tabulate(self.registradores.instantanea(),
                       headers=['Num','Nome','Hex','Dec']))
        print('\n=== Estado Final da Memória (.text) ===')
        print(tabulate([(f"0x{e:08X}", c32, t, o)
                         for e,c32,t,o in self.memoria.instantanea()],
                       headers=['Endereço','Cod32','Instr','Op']))
        print('\n=== Estado Final da Memória de Dados (.data) ===')
        print(tabulate(self.memoria_dados.instantanea(),
                       headers=['Endereço','Tipo','Hex','Dec']))
        print(f"\nTempo total: {formatar_tempo(self.tempo_acumulado)}")

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
        print('\nSimulação interrompida.\n')
    finally:
        sim.exibir_estado_final()


# o PC tem que apontar para a proxima linha enquanto ele nao executar 
# ou seja, se o PC deve apontar para a proxima linha, ele começa na linha 1 e so vai para a segunda linha quando ele executar a primeira