Simulador MIPS em Python

Simulador passo a passo de instruções MIPS com visualização de tempo de execução, PC, tipo de instrução e registradores.

📋 Sumário

Visão Geral

📁 Estrutura do Repositório

🚀 Funcionalidades

🔧 Instalação

🏗️ Arquitetura e Classes

📈 Fluxo de Execução

📋 Exemplo de Uso

🧪 Testes

🤝 Contribuição

⚖️ Licença

📦 Visão Geral

Este projeto implementa um simulador simples de CPU MIPS em Python. A cada instrução, exibe:

Tempo acumulado (segundos)

PC (Program Counter, em hexadecimal)

Tipo (I, J ou R)

Texto da instrução

Tabela de Registradores (endereço, nome e valor)

📁 Estrutura do Repositório

mips-simulator/
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions para CI
├── examples/
│   └── programa.txt         # Programa MIPS de exemplo
├── src/
│   ├── config.py            # Lê config_CPU
│   ├── parser.py            # Parser de instruções
│   ├── cpu.py               # Lógica de execução
│   ├── pc.py                # Contador de programa
│   ├── registers.py         # Manipulação de registradores
│   ├── memory.py            # (Opcional) Memória load/store
│   └── simulator.py         # Ponto de entrada
├── tests/
│   └── test_simulator.py    # Testes unitários
├── requirements.txt         # Dependências
├── LICENSE
└── README.md

🚀 Funcionalidades

Leitura de config_CPU = [clock, ciclos_I, ciclos_J, ciclos_R]

Parser de arquivo .txt com instruções MIPS

Cálculo de tempo por instrução: T = 1/clock × ciclos

Incremento de PC em 4 bytes e suporte a loops/jumps

Exibição detalhada a cada passo

Tabela de registradores atualizável

Modularidade em classes para fácil extensão

🔧 Instalação

Clone o repositório:

git clone https://github.com/SEU_USUARIO/mips-simulator.git
cd mips-simulator

Crie e ative um venv:

python3 -m venv venv
source venv/bin/activate  # macOS/Linux
venv\\Scripts\\activate # Windows

Instale dependências:

pip install -r requirements.txt

🏗️ Arquitetura e Classes

Classe

Descrição

Config

Carrega config_CPU e expõe clock e ciclos.

InstructionParser

Interpreta arquivo .txt e gera instruções.

MIPSInstruction

Representa instrução (tipo, opcode, operandos).

ProgramCounter

Gerencia PC, incrementa e faz saltos.

RegisterFile

Mantém tabela de registradores (nome, endereço, valor).

Memory

Simula memória load/store (opcional).

CPU

Executa instruções e atualiza registradores/memória.

Simulator

Orquestra leitura, execução e exibição.

📈 Fluxo de Execução

Inicialização

Config lê parâmetros de clock e ciclos.

InstructionParser carrega instruções.

Instancia ProgramCounter, RegisterFile, CPU.

Execução (loop)

Busca instrução via PC.

Calcula tempo = ciclos_tipo * (1/clock).

Acumula em tempo_total.

CPU.execute(instruction) atualiza estado.

ProgramCounter.advance() (ou jump).

Exibe estado: tempo, PC, tipo, instrução e registradores.

📋 Exemplo de Uso

Arquivo examples/programa.txt:

config_CPU = [2.5e9, 4, 3, 1]
li $t0, 5
li $t1, 10
add $t2, $t0, $t1

Execute:

python -m src.simulator examples/programa.txt

Saída:

Tempo: 4.0e-09 s | PC: 0x00 | Tipo: I | Inst: li $t0, 5
Registers:
| Endereço Mem. | Registrador | Valor |
| ------------: |:-----------:|------:|
|       0x153A47|    $t0      |     5 |
...

🧪 Testes

Os testes estão em tests/.

Execute com pytest:

pytest --cov=src

🤝 Contribuição

Fork e branch (feature/x)

Commit atômico e doc clara

PR com descrição das mudanças

⚖️ Licença

Este projeto está sob a licença livre.
