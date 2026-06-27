# 📝 ClarifAi
[![Python Version](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Quality](https://img.shields.io/badge/Code%20Quality-A-%23ff69b4.svg)](https://github.com)

## 📚 Table of Contents
1. [Summary](#summary)
2. [Features](#features)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Project Structure](#project-structure)
6. [Contributing](#contributing)
7. [License](#license)

## 📄 Summary
A Python project that utilizes base64, pyngrok, and subprocess to create an invoice auditor.

## ▶️ Demo 
https://clarifai-qzkvzvr5m77oayiw7h4iqe.streamlit.app/

## 🎉 Features
* 📊 Audits invoices for discrepancies
* 📈 Utilizes base64 for encoding and decoding
* 🚀 Leverages pyngrok for secure tunneling
* 🔄 Executes system commands using subprocess

## 📦 Installation
To install the required dependencies, run the following command:
```bash
pip install -r requirements.txt
```
Then, install pyngrok using:
```bash
pip install pyngrok
```

## 📊 Usage
To use the invoice auditor, simply execute the following command:
```bash
python invoice_auditor.py
```
Replace `invoice_auditor.py` with the actual script name.

## 🗂️ Project Structure
```markdown
invoice-auditor/
│
├── README.md
├── requirements.txt
├── invoice_auditor.py
├── utils
│   ├── __init__.py
│   ├── base64_utils.py
│   ├── pyngrok_utils.py
│   └── subprocess_utils.py
├── tests
│   ├── __init__.py
│   ├── test_base64_utils.py
│   ├── test_pyngrok_utils.py
│   └── test_subprocess_utils.py
└── .gitignore
```

## 🤝 Contributing
Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
👍
