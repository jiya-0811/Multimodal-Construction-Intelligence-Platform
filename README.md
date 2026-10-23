# Multimodal Construction Intelligence Platform

An AI-powered web application designed to support construction-site analysis using multimodal inputs such as images and text. The platform aims to help users interpret construction-related visual information and generate useful insights with the help of Google's Gemini AI.

## 🚀 Overview

The Multimodal Construction Intelligence Platform combines a web interface with AI-powered image understanding to assist in construction-related inspection and analysis.

Users can upload construction-site images and provide relevant prompts to obtain AI-generated observations and insights.

## ✨ Features

- **AI-Powered Image Analysis:** Analyze uploaded construction-related images using Google's Gemini API.
- **Multimodal Interaction:** Combine image input with text prompts for contextual analysis.
- **Web-Based Interface:** Access the application through a browser.
- **FastAPI Backend:** Handle application requests using FastAPI.
- **Configurable AI Model:** Configure the Gemini model through environment variables.
- **Cloud Deployment:** Designed for deployment on a hosting platform such as Render.

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** HTML, CSS, JavaScript
- **AI Integration:** Google Gemini API
- **ASGI Server:** Uvicorn
- **Deployment:** Docker and Render
- **Version Control:** Git and GitHub

## 📁 Project Structure

```text
Multimodal-Construction-Intelligence-Platform/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── static/
│       └── index.html
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
├── render.yaml
└── requirements.txt
```

## ⚙️ Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/jiya-0811/Multimodal-Construction-Intelligence-Platform.git
cd Multimodal-Construction-Intelligence-Platform
```

### 2. Create a virtual environment

**Windows:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root and add your own Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
MAX_IMAGE_MB=8
```

Obtain an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

**Security:** Never commit your `.env` file or expose your API key in public repositories, screenshots, or logs. Keep `.env.example` limited to placeholder values.

### 5. Run the application

```bash
python -m uvicorn app.main:app --reload
```

Open the application in your browser:

http://127.0.0.1:8000

## 🌐 Deployment

The project includes a `Dockerfile` and `render.yaml` for deployment configuration.

To deploy using Render:

1. Sign in to [Render](https://render.com/).
2. Create a new Web Service and connect this GitHub repository.
3. Select the `main` branch.
4. Configure the required environment variables in Render's dashboard.
5. Deploy the service and review the deployment logs.
6. Open the generated public URL after the service becomes live.

Ensure that the deployment configuration matches the application's actual runtime and startup requirements.

## 🔐 Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | API key used to access Google's Gemini API |
| `GEMINI_MODEL` | Gemini model identifier |
| `MAX_IMAGE_MB` | Maximum permitted image size in MB, if enforced by the application |

## 🎯 Use Cases

Potential use cases include:

- Construction-site image review
- Visual documentation and inspection support
- AI-assisted interpretation of construction imagery
- Preliminary identification of visible site conditions
- Construction-related question answering using image context

AI-generated results should be treated as decision-support information, not as a substitute for professional structural assessments, safety inspections, or engineering approval.

## 🔮 Future Enhancements

- Construction progress monitoring
- PPE and site-safety observation support
- Defect detection and reporting
- Automated inspection summaries
- Historical image comparison
- PDF report generation
- User authentication and project history

These are potential future enhancements and may not be implemented in the current version.

## 🤝 Contributing

Contributions, suggestions, and bug reports are welcome. Fork the repository, create a feature branch, and submit a pull request describing your changes.

## 👩‍💻 Author

**Jiya**

GitHub: [@jiya-0811](https://github.com/jiya-0811)

## 📄 License

No license has been specified yet. Add a `LICENSE` file before distributing the project under an open-source license.
