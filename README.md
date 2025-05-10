# 🧠 Simulador de MIPS – Python

Este é um simulador educacional de instruções MIPS, que lê um arquivo `.txt` com a configuração da CPU e as instruções, executa linha por linha, calcula o tempo de execução com base nos ciclos e atualiza os registradores.

---

## 🚀 Como funciona?

1. Lê a configuração da CPU (`config_CPU`) da primeira linha.
2. Interpreta cada instrução MIPS (tipos R, I, J).
3. Calcula o tempo com base nos ciclos por tipo de instrução.
4. Atualiza o PC (contador de programa) de 4 em 4 bytes.
5. Atualiza a tabela de registradores com valores.
6. Exibe passo a passo: tempo acumulado, PC, tipo, instrução.

---

## 📁 Estrutura do Repositório

mips-simulator/
├── .github/
│ └── workflows/
│ └── ci.yml # GitHub Actions para testes
├── examples/
│ └── programa.txt # Exemplo de programa MIPS
├── src/
│ ├── config.py # Leitura e validação da config_CPU
│ ├── parser.py # Análise sintática das instruções
│ ├── cpu.py # Lógica principal de execução
│ ├── pc.py # Contador de Programa
│ ├── registers.py # Manipulação dos registradores
│ ├── memory.py # (Opcional) memória simulada
│ └── simulator.py # Ponto de entrada do simulador
├── tests/
│ └── test_simulator.py # Testes unitários
├── requirements.txt # Dependências do projeto
├── LICENSE
└── README.md


---

## ⚙️ Exemplo de uso

Arquivo `programa.txt`:

config_CPU = [2.5e9, 4, 3, 1]
li $t0, 5
li $t1, 10
add $t2, $t0, $t1


Execução:

```bash
python src/simulator.py examples/programa.txt

Saída esperada:

⏱ Tempo: 0.4 ns | 📄 PC: 0x00 | 🆔 Tipo: I | ⚙️ li $t0, 5
⏱ Tempo: 0.8 ns | 📄 PC: 0x04 | 🆔 Tipo: I | ⚙️ li $t1, 10
⏱ Tempo: 1.2 ns | 📄 PC: 0x08 | 🆔 Tipo: R | ⚙️ add $t2, $t0, $t1

🧾 Tabela de Registradores
Endereço Mem.	Registrador	Valor
0x153A47	$t0	5
0x1576BB	$t1	10
0x15AB90	$t2	15

✅ Testes
Para rodar os testes:
pytest tests/
```
