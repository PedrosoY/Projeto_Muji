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
    milissegundos = segundos * 1e3
    if milissegundos >= 1:
        return f"{milissegundos:.3f} ms"
    microssegundos = segundos * 1e6
    if microssegundos >= 1:
        return f"{microssegundos:.3f} µs"
    nanosegundos = segundos * 1e9
    return f"{nanosegundos:.3f} ns"

# --------------------------------------------------------------------------------
# Configuração da CPU (clock e pesos para tipos de instruções)
# --------------------------------------------------------------------------------
class ConfiguracaoCPU:
    def __init__(self, itens_config: list[str]):
        self.fatores_unidades = {'hz': 1, 'khz': 1e3, 'mhz': 1e6, 'ghz': 1e9}
        self.frequencia_clock_hz: float = 1e9
        self.pesos_instrucao: dict[str, int] = {'I': 1, 'J': 1, 'R': 1}
        self._parsear_itens(itens_config)
        self.periodo_clock_segundos: float = 1.0 / self.frequencia_clock_hz

    def _parsear_itens(self, itens_config: list[str]) -> None:
        for item in itens_config:
            texto = item.strip().lower()
            # Configuração de frequência de clock
            correspondencia = re.match(r'([\d\.]+)\s*([kmg]?hz)', texto)
            if correspondencia:
                valor, unidade = correspondencia.groups()
                self.frequencia_clock_hz = float(valor) * self.fatores_unidades[unidade]
                continue
            # Configuração de peso por tipo de instrução
            correspondencia_peso = re.match(r'(i|j|r)\s*=\s*(\d+)', texto)
            if correspondencia_peso:
                tipo, peso = correspondencia_peso.groups()
                self.pesos_instrucao[tipo.upper()] = int(peso)

# --------------------------------------------------------------------------------
# Banco de registradores MIPS com histórico de modificações
# --------------------------------------------------------------------------------
class BancoDeRegistradores:
    def __init__(self):
        nomes_registradores = [
            'zero','at','v0','v1','a0','a1','a2','a3',
            't0','t1','t2','t3','t4','t5','t6','t7',
            's0','s1','s2','s3','s4','s5','s6','s7',
            't8','t9','k0','k1','gp','sp','fp','ra'
        ]
        self.valores: dict[str, int] = {f"${nome}": 0 for nome in nomes_registradores}
        self.historico_modificacoes: list[str] = []

    def escrever_registrador(self, nome_reg: str, valor: int) -> None:
        if nome_reg == '$zero':
            return  # Registrador zero é sempre 0
        self.valores[nome_reg] = valor
        # Atualiza histórico de modificações
        if nome_reg in self.historico_modificacoes:
            self.historico_modificacoes.remove(nome_reg)
        self.historico_modificacoes.append(nome_reg)
        if len(self.historico_modificacoes) > len(self.valores):
            self.historico_modificacoes.pop(0)

    def ler_registrador(self, nome_reg: str) -> int:
        return self.valores.get(nome_reg, 0)

    def snapshot_registradores(self, max_linhas: int = 5) -> list[tuple[int,str,str,int]]:
        linhas = []
        ultimos = self.historico_modificacoes[-max_linhas:]
        for nome in reversed(ultimos):
            idx = list(self.valores.keys()).index(nome)
            valor = self.valores[nome]
            linhas.append((idx, nome, hex(valor), valor))
        return linhas

# --------------------------------------------------------------------------------
# Memória de programa (.text) e rótulos (labels)
# --------------------------------------------------------------------------------
class MemoriaDePrograma:
    def __init__(self):
        self.lista_instrucoes: list[str] = []
        self.rotulos: dict[str, int] = {}

    def carregar_programa(self, caminho: Path, offset_linhas: int = 0) -> None:
        with open(caminho, 'r') as arquivo:
            indice = 0
            for num_linha, conteudo in enumerate(arquivo):
                if num_linha < offset_linhas:
                    continue
                texto = conteudo.strip()
                if not texto or texto.startswith('#'):
                    continue
                if texto.endswith(':'):
                    nome_rotulo = texto[:-1]
                    self.rotulos[nome_rotulo] = indice
                else:
                    self.lista_instrucoes.append(texto)
                    indice += 1

    def snapshot_memoria_programa(self) -> list[tuple[int,str,str,str]]:
        resultado = []
        for idx, instrucao in enumerate(self.lista_instrucoes):
            endereco_byte = idx * 4
            codigo32 = hex(abs(hash(instrucao)) & 0xFFFFFFFF)
            operacao = instrucao.split()[0]
            resultado.append((endereco_byte, codigo32, instrucao, operacao))
        return resultado

    def obter_instrucao(self, indice_instrucao: int) -> str | None:
        if 0 <= indice_instrucao < len(self.lista_instrucoes):
            return self.lista_instrucoes[indice_instrucao]
        return None

# --------------------------------------------------------------------------------
# Memória de dados (RAM) com detecção de strings
# --------------------------------------------------------------------------------
class MemoriaDeDados:
    def __init__(self, tamanho_bytes: int = 1024):
        self.tamanho_bytes = tamanho_bytes
        self.memoria = bytearray(tamanho_bytes)
        self.mapa_escrito: dict[int, tuple[int, object]] = {}

    def escrever_memoria(self, endereco: int, valor, tamanho: int) -> None:
        if endereco < 0 or endereco + tamanho > self.tamanho_bytes:
            raise ValueError(f"Endereço {endereco} fora do intervalo de memória")
        if isinstance(valor, str):
            bytes_valor = valor.encode('ascii')
            if len(bytes_valor) != tamanho:
                raise ValueError("Tamanho da string não corresponde ao tamanho especificado")
        else:
            bytes_valor = int(valor).to_bytes(tamanho, 'little', signed=True)
        self.memoria[endereco:endereco+tamanho] = bytes_valor
        self.mapa_escrito[endereco] = (tamanho, valor)

    def ler_memoria(self, endereco: int, tamanho: int):
        if endereco < 0 or endereco + tamanho > self.tamanho_bytes:
            raise ValueError(f"Endereço {endereco} fora do intervalo de memória")
        fatia = self.memoria[endereco:endereco+tamanho]
        if endereco in self.mapa_escrito and isinstance(self.mapa_escrito[endereco][1], str):
            return fatia.decode('ascii')
        return int.from_bytes(fatia, 'little', signed=True)

    def snapshot_memoria_dados(self) -> list[tuple[str,str,str,object]]:
        linhas = []
        enderecos_ordenados = sorted(self.mapa_escrito)
        visitados = set()
        i = 0
        while i < len(enderecos_ordenados):
            endereco = enderecos_ordenados[i]
            if endereco in visitados:
                i += 1
                continue
            tamanho, valor_original = self.mapa_escrito[endereco]
            # Detecção de sequência de bytes ASCII para strings
            if tamanho == 1:
                seq = []
                pos = endereco
                while pos in self.mapa_escrito and self.mapa_escrito[pos][0] == 1:
                    byte = self.memoria[pos]
                    caractere = chr(byte)
                    if caractere in string.printable and caractere != '\x00':
                        seq.append(caractere)
                        visitados.add(pos)
                        pos += 1
                    else:
                        break
                if len(seq) > 1:
                    texto = ''.join(seq)
                    linhas.append((f"0x{endereco:08X}", 'String', repr(texto), None))
                    while i < len(enderecos_ordenados) and enderecos_ordenados[i] < pos:
                        i += 1
                    continue
            # Dados não string ou isolados
            fatia = self.memoria[endereco:endereco+tamanho]
            valor_inteiro = int.from_bytes(fatia, 'little', signed=True)
            repr_hex = f"\"{valor_original}\"" if isinstance(valor_original, str) else hex(valor_inteiro)
            tipo_memoria = {1:'Byte',2:'Halfword',4:'Word'}.get(tamanho, f'{tamanho}B')
            linhas.append((f"0x{endereco:08X}", tipo_memoria, repr_hex, valor_inteiro))
            visitados.add(endereco)
            i += 1
        return linhas

# --------------------------------------------------------------------------------
# Relógio de ciclos
# --------------------------------------------------------------------------------
class RelogioCiclos:
    def __init__(self):
        self.contador_ciclos: int = 0

    def tick(self) -> None:
        self.contador_ciclos += 1

# --------------------------------------------------------------------------------
# Decodificação de instrução MIPS
# --------------------------------------------------------------------------------
class InstrucaoMIPS:
    def __init__(self, texto_instrucao: str):
        self.texto_instrucao = texto_instrucao
        partes = texto_instrucao.replace(',', '').split()
        self.operacao = partes[0].lower()
        self.argumentos = partes[1:]
        if self.operacao in ('j', 'jal'):
            self.tipo_instrucao = 'J'
        elif self.operacao in ('add', 'sub', 'and', 'or'):
            self.tipo_instrucao = 'R'
        else:
            self.tipo_instrucao = 'I'
        self.codigo_maquina_32 = hex(abs(hash(texto_instrucao)) & 0xFFFFFFFF)

# --------------------------------------------------------------------------------
# Simulador MIPS principal
# --------------------------------------------------------------------------------
class SimuladorMIPS:
    def __init__(self, caminho_arquivo: Path):
        linhas = caminho_arquivo.read_text().splitlines()
        linha_config = next(l for l in linhas if l.lower().startswith('config_cpu'))
        conteudo_config = re.search(r'\[(.*)\]', linha_config).group(1)
        itens_config = [i.strip() for i in conteudo_config.split(',')]
        self.config_cpu = ConfiguracaoCPU(itens_config)

        self.memoria_programa = MemoriaDePrograma()
        self.memoria_programa.carregar_programa(caminho_arquivo, offset_linhas=1)

        self.memoria_dados = MemoriaDeDados(1024)
        self.banco_registradores = BancoDeRegistradores()
        self.program_counter: int = 0
        self.relogio = RelogioCiclos()
        self.tempo_acumulado: float = 0.0

    def executar_passo(self) -> bool:
        indice_instrucao = self.program_counter // 4
        texto = self.memoria_programa.obter_instrucao(indice_instrucao)
        if texto is None:
            return False
        instrucao = InstrucaoMIPS(texto)
        # Avança PC antes de executar
        self.program_counter += 4
        # Atualiza relógio e tempo
        self.relogio.tick()
        peso = self.config_cpu.pesos_instrucao[instrucao.tipo_instrucao]
        self.tempo_acumulado += peso * self.config_cpu.periodo_clock_segundos

        # Execução das operações MIPS
        if instrucao.operacao == 'li':
            rd, valor = instrucao.argumentos
            v = self._interpretar_valor_imediato(valor)
            self.banco_registradores.escrever_registrador(rd, v)
        elif instrucao.operacao == 'j':
            self._instrucao_jump(instrucao.argumentos[0])
            return True
        elif instrucao.operacao == 'la':
            self._instrucao_load_address(instrucao.argumentos)
        elif instrucao.operacao == 'add':
            rd, r1, r2 = instrucao.argumentos
            soma = self.banco_registradores.ler_registrador(r1) + self.banco_registradores.ler_registrador(r2)
            self.banco_registradores.escrever_registrador(rd, soma)
        elif instrucao.operacao == 'addi':
            rd, rs, imm = instrucao.argumentos
            resultado = self.banco_registradores.ler_registrador(rs) + int(imm, 0)
            self.banco_registradores.escrever_registrador(rd, resultado)
        elif instrucao.operacao == 'beq':
            self._instrucao_branch_equal(instrucao.argumentos)
        elif instrucao.operacao in ('sw', 'sb'):
            self._instrucao_store(instrucao.operacao, instrucao.argumentos)

        self._exibir_estado(instrucao, indice_instrucao)
        return True

    # Métodos auxiliares para formatos e instruções específicas
    def _interpretar_valor_imediato(self, valor: str) -> int:
        if valor.startswith("'") and valor.endswith("'"):
            return ord(valor[1:-1])
        return int(valor, 0)

    def _instrucao_jump(self, rotulo: str) -> None:
        if rotulo not in self.memoria_programa.rotulos:
            raise ValueError(f"Rótulo '{rotulo}' não definido")
        self.program_counter = self.memoria_programa.rotulos[rotulo] * 4

    def _instrucao_load_address(self, argumentos: list[str]) -> None:
        rd, arg = argumentos
        if re.match(r'^(-?0x[0-9a-f]+|-?\d+)$', arg, re.IGNORECASE):
            endereco = int(arg, 0)
        else:
            if arg not in self.memoria_programa.rotulos:
                raise ValueError(f"Rótulo '{arg}' não definido")
            endereco = self.memoria_programa.rotulos[arg] * 4
        self.banco_registradores.escrever_registrador(rd, endereco)

    def _instrucao_branch_equal(self, argumentos: list[str]) -> None:
        rs, rt, rotulo = argumentos
        if self.banco_registradores.ler_registrador(rs) == self.banco_registradores.ler_registrador(rt):
            if rotulo not in self.memoria_programa.rotulos:
                raise ValueError(f"Rótulo '{rotulo}' não definido")
            self.program_counter = self.memoria_programa.rotulos[rotulo] * 4

    def _instrucao_store(self, operacao: str, argumentos: list[str]) -> None:
        rt, offbase = argumentos
        correspondencia = re.match(r'(-?0x[0-9a-f]+|-?\d+)\((\$[\w]+)\)', offbase, re.IGNORECASE)
        if not correspondencia:
            raise ValueError(f"Formato inválido para {operacao}: {offbase}")
        deslocamento, registrador_base = correspondencia.groups()
        endereco = self.banco_registradores.ler_registrador(registrador_base) + int(deslocamento, 0)
        valor = self.banco_registradores.ler_registrador(rt)
        tamanho = 1 if operacao == 'sb' else 4
        if operacao == 'sb':
            valor &= 0xFF
        self.memoria_dados.escrever_memoria(endereco, valor, tamanho)

    def _exibir_estado(self, instrucao: InstrucaoMIPS, exec_idx: int) -> None:
        cabecalho = [
            ['Tempo', formatar_tempo(self.tempo_acumulado)],
            ['Ciclos', self.relogio.contador_ciclos],
            ['PC', f"0x{self.program_counter:08X}"],
            ['Tipo', instrucao.tipo_instrucao],
            ['Instrucao', instrucao.texto_instrucao]
        ]
        print(tabulate(cabecalho, tablefmt='plain'))
        print('\nRegistradores:')
        print(tabulate(self.banco_registradores.snapshot_registradores(), headers=['Num','Reg','Hex','Dec']))
        print('\nMemoria de Programa (.text):')
        exec_idx = (self.program_counter - 4) // 4
        total = len(self.memoria_programa.lista_instrucoes)
        inicio = max(0, exec_idx - 2)
        fim = min(total, exec_idx + 3)
        linhas = []
        for idx in range(inicio, fim):
            endereco = idx * 4
            instr = self.memoria_programa.lista_instrucoes[idx]
            codigo32 = hex(abs(hash(instr)) & 0xFFFFFFFF)
            oper = instr.split()[0]
            if idx == exec_idx:
               marcador = '-->'   # instrução atual
            elif idx == exec_idx + 1:
                marcador = '->'   # próxima instrução (PC)
            else:
                marcador = ' '
            linhas.append((marcador, f"0x{endereco:08X}", codigo32, instr, oper))
        print(tabulate(linhas, headers=['','End','Cod32','Instr','Op']))
        print('\nMemoria de Dados (.data):')
        print(tabulate(self.memoria_dados.snapshot_memoria_dados(), headers=['Endereco','Tipo','Hex','Dec']))
        print('\n' + '='*60 + '\n')

    def exibir_estado_final(self) -> None:
        print('\n=== Estado Final dos Registradores ===')
        print(tabulate(self.banco_registradores.snapshot_registradores(max_linhas=5), headers=['Num','Reg','Hex','Dec']))
        print('\n=== Memoria de Programa (.text) Final ===')
        programa = [(f"0x{e:08X}", c32, instr, oper)
                    for e, c32, instr, oper in self.memoria_programa.snapshot_memoria_programa()]
        print(tabulate(programa, headers=['End','Cod32','Instr','Op']))
        print('\n=== Memoria de Dados (.data) Final ===')
        print(tabulate(self.memoria_dados.snapshot_memoria_dados(), headers=['Endereco','Tipo','Hex','Dec']))
        print(f"\nTempo total: {formatar_tempo(self.tempo_acumulado)}")

# --------------------------------------------------------------------------------
# Execução principal
# --------------------------------------------------------------------------------
if __name__ == '__main__':
    arquivo_codigo = Path(__file__).parent / 'codigo_executavel.txt'
    simulador = SimuladorMIPS(arquivo_codigo)
    print('Simulador MIPS iniciado. Pressione Enter para próximo passo ou Ctrl+C para encerrar.\n')
    try:
        while simulador.executar_passo():
            input()
    except KeyboardInterrupt:
        print('\nSimulação interrompida pelo usuário.\n')
    finally:
        simulador.exibir_estado_final()
