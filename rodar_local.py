"""Runner LOCAL do conector Nubank ao vivo.

Rode ESTE script na SUA maquina (nunca num servidor). Ele:
  1. pede seu CPF e senha do Nubank (a senha nao aparece na tela);
  2. faz o login por QR code no primeiro uso (escaneie no app do Nubank);
  3. salva um certificado .p12 local pra reusar depois (sem novo login);
  4. puxa conta + cartao, categoriza e mostra as analises;
  5. salva seus dados em dados/meus_dados.csv (ignorado pelo Git).

Uso:
    python rodar_local.py

Suas credenciais ficam só na sua maquina. O .gitignore do projeto ja impede
que o certificado (*.p12) e a pasta dados/ subam pro GitHub.
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from financas_ai.conectores import nubank_online
from financas_ai.core import categorizador, analise


def real(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    print("=" * 56)
    print("  Finanças AI — conexão com o Nubank (LOCAL)")
    print("=" * 56)
    print("Suas credenciais ficam só nesta máquina.\n")

    cpf = input("CPF (só números): ").strip()
    senha = getpass.getpass("Senha do app Nubank (não aparece): ").strip()

    cert = "nubank_cert.p12"
    if not Path(cert).exists():
        print("\nPrimeiro acesso: um QR code vai aparecer abaixo.")
        print("No app do Nubank: Perfil → Me ajuda → ... ou 'Acesso pelo site',")
        print("e escaneie o código.\n")

    try:
        df = nubank_online.ler(cpf, senha, cert)
    except Exception as e:
        msg = str(e)
        print(f"\n❌ Não consegui conectar: {msg}")
        if "403" in msg:
            print("O Nubank bloqueou a requisição da API não-oficial (anti-robô).")
            print("Isso é instável por natureza. Use o caminho confiável:")
            print("  exporte o extrato (OFX/CSV) e rode:  python rodar_arquivo.py SEU_EXTRATO.ofx")
        else:
            print("Confira CPF/senha e tente de novo. (Erros do Nubank são comuns na 1ª vez.)")
        sys.exit(1)

    df = categorizador.categorizar(df)

    # salva para reuso/offline (pasta ignorada pelo Git)
    Path("dados").mkdir(exist_ok=True)
    df.to_csv("dados/meus_dados.csv", index=False)

    print("\n" + "=" * 56)
    print(f"✅ {len(df)} transações carregadas da sua conta Nubank")
    print(f"   Cobertura do categorizador: {categorizador.cobertura(df)}%")
    print("=" * 56)

    print("\n>> Seus gastos por categoria:")
    for cat, val in analise.gastos_por_categoria(df).items():
        print(f"   {cat:16} {real(val)}")

    print("\n>> Evolução mensal (entradas / saídas / saldo):")
    print(analise.evolucao_mensal(df).apply(lambda c: c.map(real)).to_string())

    print("\n>> Possíveis cobranças recorrentes:")
    for _, r in analise.possiveis_recorrencias(df).head(8).iterrows():
        print(f"   {r['exemplo'][:34]:34} ~{real(abs(r['valor_medio']))}/mês ({r['ocorrencias']} meses)")

    print("\nDados salvos em dados/meus_dados.csv (não vai pro GitHub).")


if __name__ == "__main__":
    main()
