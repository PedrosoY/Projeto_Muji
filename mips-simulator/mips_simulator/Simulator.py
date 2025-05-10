from pathlib import Path

# Salvar registradores usados
registradores = {}

# Caminho absoluto para o arquivo na mesma pasta do script
arquivo = Path(__file__).parent / "codigo_executavel.txt"

# Função Li
def salvarNaMemoria(registrador, valor):
    valor_hex = hex(int(valor))
    registradores[registrador] = valor_hex
    print(f"Registrador {registrador} salvo com valor {valor_hex}")

# Função ADD
def somarDoisRegistradores(destino, r1, r2):
    v1 = int(registradores.get(r1, "0x0"), 16)
    v2 = int(registradores.get(r2, "0x0"), 16)
    soma = v1 + v2
    print(f"Somando registradores {r1} e {r2}: {hex(v1)} + {hex(v2)} = {hex(soma)}")
    print(f"Resultado armazenado no registrador {destino}: {hex(soma)}")
    salvarNaMemoria(destino, soma)

# Ler linha a linha do arquivo
with open(arquivo) as f:
    for linha in f:
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue

        partes = linha.replace(",", "").split()

        if partes[0] == "li" and len(partes) == 3:
            salvarNaMemoria(partes[1], partes[2])

        elif partes[0] == "add" and len(partes) == 4:
            somarDoisRegistradores(partes[1], partes[2], partes[3])

# Imprimir registradores finais
print("\nRegistradores Finais:")
for reg, val in registradores.items():
    print(f"{reg}: {int(val, 16)}")


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