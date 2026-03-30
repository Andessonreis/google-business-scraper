import pandas as pd
import glob
import os

# Pega todos os arquivos de partes gerados
arquivos_csv = glob.glob("output/consolidado/contadores_celular_parte_*.csv")

dataframes = []

for arquivo in arquivos_csv:
    df = pd.read_csv(arquivo)
    dataframes.append(df)

if dataframes:
    df_mestre = pd.concat(dataframes, ignore_index=True)

    # Remove duplicadas caso um negócio tenha sido pego por cruzamento de fronteiras de termos
    df_mestre = df_mestre.drop_duplicates(
        subset=["latitude", "longitude"], keep="first"
    )

    # Salva o resultado final único
    df_mestre.to_csv("output/consolidado/PLANILHA_MESTRE_FINAL.csv", index=False)
    df_mestre.to_excel("output/consolidado/PLANILHA_MESTRE_FINAL.xlsx", index=False)

    print(f"✅ Sucesso! Planilha mestre gerada com {len(df_mestre)} contatos únicos.")
    print("Salvo em: output/consolidado/PLANILHA_MESTRE_FINAL.xlsx")
else:
    print("⚠️ Nenhum arquivo de parte encontrado para juntar.")
