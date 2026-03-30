import requests

url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-100-mun.json"
data = requests.get(url).json()

linhas = []

UF = {
    "29": "BA",
    # Você pode adicionar mais estados aqui depois
}

categorias = [
    "Clínica",
    "Médico",
    "Dentista",
    "Clínica Odontológica",
    "Clínica de fisioterapia",
    "Psiquiatra",
    "Psicólogo",
    "Terapeuta",
    "Nutricionista",
    "Escola de enfermagem",
    "Assistente Social",
    "Farmácia",
    "Fonoaudiólogo",
    "Laboratório",
    "Personal trainer",
]

for cidade in data["features"]:
    props = cidade["properties"]
    nome = props["name"]
    codigo_ibge = props["id"]

    uf_codigo = codigo_ibge[:2]
    estado = UF.get(uf_codigo)

    # ignorar Sergipe e estados que não estão no dicionário UF
    if not estado or estado == "SE":
        continue

    for categoria in categorias:
        linhas.append(f"{categoria} em {nome} {estado}")

# Já salva direto como input.txt para o main.py usar
with open("input.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(linhas))

print(f"Arquivo gerado com sucesso! Total de buscas: {len(linhas)}")
