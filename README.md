# 📸 Organizador de Fotos por Data com Detecção de Duplicatas

## 📖 Sobre o Projeto

O Organizador de Fotos é uma aplicação desktop desenvolvida em Python para auxiliar na organização de grandes volumes de fotos e vídeos armazenados em computadores ou HDs externos.

A aplicação identifica automaticamente a data dos arquivos utilizando metadados EXIF (quando disponíveis) ou a data do próprio arquivo, organizando o conteúdo em uma estrutura de pastas cronológica.

Além disso, o sistema detecta arquivos duplicados através de comparação por hash MD5, permitindo ao usuário remover cópias redundantes e liberar espaço de armazenamento.

---

## ✨ Funcionalidades

* Organização automática de fotos e vídeos por data.
* Leitura de metadados EXIF de imagens.
* Suporte a HDs externos e pastas locais.
* Criação automática de estrutura de pastas por:

  * Ano
  * Ano/Mês
  * Ano/Mês/Dia
  * Ano/Mês com nome do mês
* Detecção de arquivos duplicados utilizando hash MD5.
* Exclusão segura de arquivos duplicados.
* Opção de copiar ou mover arquivos.
* Interface gráfica desenvolvida com Tkinter.
* Barra de progresso em tempo real.
* Registro de atividades (log).

---

## 🛠 Tecnologias Utilizadas

* Python 3.10+
* Tkinter
* Pillow (PIL)
* Hashlib
* OS
* Shutil
* Threading

---

## 📂 Estrutura do Projeto

```text
organizador-fotos/
│
├── organizador_fotos.py
├── README.md
├── requirements.txt
└── screenshots/
    ├── tela_principal.png
    └── duplicatas.png
```

---

## 📷 Formatos Suportados

### Imagens

* JPG
* JPEG
* PNG
* GIF
* BMP
* TIFF
* HEIC
* HEIF
* WEBP
* RAW
* CR2
* NEF
* ARW
* DNG
* ORF
* RW2
* PEF
* SRW

### Vídeos

* MP4
* MOV
* AVI
* MKV
* M4V
* 3GP
* WMV
* FLV
* MTS
* M2TS
* MPG
* MPEG

---

## ⚙️ Como Funciona

### 1. Escaneamento

O sistema percorre recursivamente todas as subpastas da origem selecionada e identifica arquivos compatíveis.

### 2. Identificação da Data

Para imagens:

1. Tenta obter a data EXIF.
2. Caso não exista, utiliza a data do arquivo.

Para vídeos:

* Utiliza a data do arquivo.

### 3. Organização

Os arquivos são copiados ou movidos para uma nova estrutura de diretórios baseada na data identificada.

Exemplo:

```text
2024/
└── 03 - Março/
    ├── IMG001.jpg
    ├── IMG002.jpg

2025/
└── 01 - Janeiro/
    ├── IMG003.jpg
```

### 4. Detecção de Duplicatas

Cada arquivo recebe uma assinatura única (hash MD5).

Arquivos com o mesmo hash são considerados duplicados.

Exemplo:

```text
foto.jpg
foto (1).jpg
```

O sistema mantém apenas uma cópia original e permite remover as demais.

---

## 🚀 Instalação

Clone o repositório:

```bash
git clone https://github.com/seu-usuario/organizador-fotos.git
```

Acesse a pasta:

```bash
cd organizador-fotos
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute:

```bash
python organizador_fotos.py
```

---

## 📦 Dependências

Arquivo requirements.txt

```text
Pillow>=10.0.0
```

---

## 🔒 Segurança

Antes de excluir qualquer arquivo duplicado, o sistema solicita confirmação do usuário.

Nenhum arquivo original é removido automaticamente.

---

## 📈 Possíveis Melhorias Futuras

* Suporte a banco de dados SQLite.
* Geração de relatórios em PDF.
* Visualização de miniaturas.
* Comparação visual de imagens semelhantes.
* Backup automático antes da exclusão.
* Exportação de logs.
* Tema claro/escuro configurável.

---

## 👩‍💻 Autora

Amanda Roque

Estudante de Ciência de Dados e desenvolvedora de soluções para automação e organização de arquivos utilizando Python.

---

## 📄 Licença

Este projeto está licenciado sob a licença MIT.
