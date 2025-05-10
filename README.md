Simulador MIPS em Python

Este projeto implementa um simulador de instruções MIPS em Python, permitindo a leitura de um programa em um arquivo de texto e a execução passo a passo, mostrando informações de tempo de execução, contador de programa (PC), tipo de instrução e tabela de registradores.

📂 Estrutura do Projeto

mips-simulator/
├── README.md               # Documentação do projeto
├── requirements.txt        # Dependências do projeto
├── config/                 # Arquivos de configuração
│   └── cpu_config.txt      # Configuração ex: config_CPU = [Clock, TipoI, TipoJ, TipoR]
├── src/                    # Código-fonte principal
│   ├── __init__.py
│   ├── parser.py           # Parser de instruções e arquivo de entrada
│   ├── config.py           # Leitura e interpretação de config_CPU
│   ├── cpu.py              # Classe CPU e lógica de execução de instruções
│   ├── pc.py               # Classe ProgramCounter (PC)
│   ├── registers.py        # Classe RegisterFile (tabela de registradores)
│   ├── memory.py           # (Opcional) Classe Memory para operações de load/store
│   └── simulator.py        # Classe Simulator: coordena leitura, execução e exibição
└── examples/               # Exemplos de uso
    └── programa.txt        # Exemplo de programa MIPS

🚀 Funcionalidades Principais

Leitura de arquivo: Carrega programa MIPS e configuração da CPU (clock, ciclos por tipo).

Cálculo de tempo: Converte ciclos em segundos usando T = 1 / Clock.

PC (Program Counter): Incremento automático de 4 em 4 bytes, com suporte a loops.

Execução passo a passo: Em cada instrução, exibe tempo acumulado, valor do PC, tipo e texto da instrução.

Tabela de registradores: Mostra endereços, nome e valor atualizado a cada instrução.

Modularidade: Organização em classes para fácil manutenção e extensão.

🔧 Instalação

Clone o repositório:

git clone https://github.com/SEU_USUARIO/mips-simulator.git
cd mips-simulator

Crie e ative um ambiente virtual:

python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\\Scripts\\activate # Windows

Instale dependências:

pip install -r requirements.txt

🏗️ Organização das Classes

Classe

Responsabilidade

Config

Carrega config_CPU do arquivo e expõe clock e ciclos por tipo.

InstructionParser

Lê o .txt, interpreta cada linha e retorna objetos MIPSInstruction.

MIPSInstruction

Representa instrução MIPS (tipo, opcode, operandos, texto bruto).

ProgramCounter

Gerencia o valor PC, incrementa em 4 e faz jumps/loops.

RegisterFile

Mantém tabela de registradores: nome, endereço (opcional) e valor.

Memory

(Opcional) Simula memória para instruções load/store.

CPU

Executa instruções: recebe MIPSInstruction, atualiza registradores e memória.

Simulator

Controla fluxo: inicializa componentes, executa em loop e exibe saída.

📈 Fluxo de Execução

Inicialização:

Config lê config_CPU = [clock, ciclos_I, ciclos_J, ciclos_R].

InstructionParser carrega lista de instruções.

ProgramCounter, RegisterFile e CPU são instanciados.

Loop de Execução:

Enquanto houver instruções:

Buscar instrução pela posição de PC.

Calcular tempo da instrução: tempo = ciclos_tipo * (1/clock).

Acumular tempo_total.

CPU.execute(instruction) atualiza registradores/memória.

ProgramCounter.advance() ou jump/loop.

Exibir:

Tempo acumulado

Valor do PC (hex)

Tipo de instrução (I, J, R)

Instrução textual

Estado atual da tabela de registradores

📋 Exemplo de Uso

Arquivo examples/programa.txt:

config_CPU = [2.5e9, 4, 3, 1]
li $t0, 5
li $t1, 10
add $t2, $t0, $t1

Executando:

python -m src.simulator examples/programa.txt

Saída esperada:

Tempo: 4.0e-09 s | PC: 0x00 | Tipo: I | Inst: li $t0, 5
Registers:
| Endereço Mem. | Registrador | Valor |
| ------------: |:-----------:|------:|
|       0x153A47|    $t0      |     5 |

Tempo: 1.6e-08 s | PC: 0x04 | Tipo: I | Inst: li $t1, 10
Registers:
| Endereço Mem. | Registrador | Valor |
|       0x1576BB|    $t1      |    10 |

... (demais instruções)

🤝 Contribuição

Fork este repositório.

Crie uma branch feature (git checkout -b feature/nova-funcionalidade).

Faça commits claros e pontuais.

Envie um Pull Request descrevendo as mudanças.

📝 Licença

Este projeto tem licença livre.
