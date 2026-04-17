import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import tempfile
import os
import json
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Validador Regulatório", layout="wide")
st.title("📄 Validador de Documentos de Fornecedores")

# --- CONFIGURAÇÃO DA API ---
# Puxa a chave do cofre do Streamlit e inicia o cliente NOVO
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

# --- PROMPT DE NEGÓCIO ---
PROMPT = """
Você é um auditor regulatório sênior. Sua tarefa é analisar os documentos fornecidos e compará-los com a nossa lista de documentos obrigatórios para homologação de fornecedores.

LISTA DE DOCUMENTOS:
- Identificação (razão social, endereço, CNPJ, e-mail, responsável técnico-ART)
- Licença de Funcionamento
- Licença Sanitária
- Fluxograma de processo
- Plano HACCP ou Resumo do Plano HACCP
- Laudo/Declaração de Pesticidas
- Laudo de Metais Pesados
- Laudo Microbiológico
- Laudo Macroscópico / Sujidades
- Certificado GFSI (SQF, FSSC 22000, BRCGS, IFS)
- Certificado ISO (9001, 22000, 14001, 45001)
- Halal e Kosher
- Declaração de Alergênicos
- Ficha técnica
- Declaração de GMO
- Declaração Gluten
- Declaração Lactose
- Declaração Irradiação
- Declaração Radiológico
- Declaração Origem
- Declaração Origem Animal
- Laudo de embalagem
- Modelo COA

Retorne EXATAMENTE a estrutura JSON abaixo, avaliando todos os itens da lista acima (se não achar, marque como Ausente). Documentos enviados que não estão na lista devem ir para "extras":
[
  {
    "Fornecedor": "Nome da Empresa",
    "Documento": "Nome conforme a lista acima",
    "Status": "Presente" ou "Ausente",
    "Tipo": "Laudo", "Declaração", "Certificado" ou "-",
    "Validade_Emissao": "DD/MM/AAAA" ou "Não consta",
    "Observacao": "Documento extra", "Faltando" ou detalhes adicionais
  }
]
"""

# --- INTERFACE DE UPLOAD ---
uploaded_files = st.file_uploader("Arraste os PDFs do fornecedor aqui", type="pdf", accept_multiple_files=True)

if st.button("Analisar Documentos") and uploaded_files:
    with st.spinner('Lendo documentos e cruzando com regras (pode levar 1-2 minutos)...'):
        try:
            arquivos_api = []
            temp_dir = tempfile.mkdtemp()
            
            # Faz o upload no formato novo do SDK com nome seguro (anti-erros de acentuação)
            for i, file in enumerate(uploaded_files):
                nome_seguro = f"documento_{i}.pdf"
                temp_path = os.path.join(temp_dir, nome_seguro)
                
                with open(temp_path, "wb") as f:
                    f.write(file.getbuffer())
                
                uploaded_api_file = client.files.upload(file=temp_path)
                arquivos_api.append(uploaded_api_file)

            # Chama a IA forçando a saída em JSON via novo SDK
            response = client.models.generate_content(
                model="gemini-1.5-pro",
                contents=[PROMPT] + arquivos_api,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            
            # Converte e exibe os dados
            dados_json = json.loads(response.text)
            df = pd.DataFrame(dados_json)

            st.subheader("📊 Resultado da Análise")
            st.dataframe(df, use_container_width=True)

            # Botão de download
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Homologacao')
            
            st.download_button(
                label="📥 Baixar Tabela em Excel",
                data=buffer.getvalue(),
                file_name="analise_homologacao.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Limpeza dos arquivos na API
            for f in arquivos_api:
                client.files.delete(name=f.name)

        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")
