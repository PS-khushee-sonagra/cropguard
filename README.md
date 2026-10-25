# 🌱 CropGuard — AI-Powered Crop Disease Assistance

CropGuard is an AI-powered agriculture assistance project designed to help farmers understand possible crop diseases, analyze visible symptoms, and access relevant crop care guidance.

The project combines AI agents, image-based analysis, weather information, and the Model Context Protocol (MCP) to support a more interactive crop assistance workflow.

## ✨ Features

- **Image-Based Crop Diagnosis:** Analyze uploaded crop images to identify possible diseases or visible symptoms.
- **AI Agent:** Uses an agent loop to decide which tools to call, observe their results, and prepare a response.
- **MCP Integration:** Connects the agent to tools through the Model Context Protocol.
- **Weather Information:** Retrieves weather information for a specified location.
- **Crop Care Guidance:** Supports farmers with relevant crop information and disease-management guidance.
- **Multilingual Interaction:** Supports Hindi and Gujarati chat alongside English, where configured.
- **Interactive Interface:** Provides a user interface for submitting crop images and questions.

## 🏗️ System Architecture

The project follows an agent-based architecture:

```text
Farmer
  |
  v
Streamlit User Interface
  |
  | Crop image, question, crop and location
  v
AI Agent
  |
  | Decides which tool to call
  v
MCP Client / Tool Connection
  |
  v
CropGuard MCP Server
  |
  +--> Image Diagnosis
  +--> Weather Information
  +--> Crop/Disease Guidance
  |
  v
Tool Results
  |
  v
AI Agent Generates Response
  |
  v
Farmer Receives Guidance
```

## 🛠️ Technology Stack

- **Python** — Core application logic
- **Streamlit** — Interactive user interface
- **Ollama** — Local language-model runtime, where configured
- **MCP (Model Context Protocol)** — Standardized connection between the agent and tools
- **AI Image Analysis** — Used to examine crop images
- **Weather API** — Used to retrieve weather information

## 🚀 Getting Started

### Prerequisites

Install the following before running the project:

- Python
- Git
- Ollama, if using the configured local language model
- The model and API credentials required by your configuration

### 1. Clone the repository

```bash
git clone https://github.com/PS-khushee-sonagra/cropguard.git
cd cropguard
```

### 2. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, use the activation method supported by your local environment.

### 3. Install dependencies

If the repository contains `requirements.txt`:

```powershell
pip install -r requirements.txt
```

Install any additional dependencies documented by the project.

### 4. Configure environment variables

If the application requires API keys, create a local `.env` file using the variable names documented in `.env.example`.

Never commit your real `.env` file or API keys to GitHub.

### 5. Configure the AI models

If the agent uses Ollama, install and start Ollama, then download the model configured by the project.

For example, if the agent is configured to use Mistral 7B:

```powershell
ollama pull mistral:7b
```

Use the actual model names configured in your project.

### 6. Run CropGuard

Start the MCP server and application using the commands configured in the repository.

For example, the MCP server can be run with the MCP CLI if that matches your setup:

```powershell
uv run --with mcp mcp run server.py:mcp
```

Run the Streamlit interface using its actual entry-point filename and the agent using the startup method defined by the project.

## 🔍 How It Works

1. The farmer submits a crop image, symptoms, or a question.
2. The AI agent evaluates the request and determines which tools may be useful.
3. The agent invokes the relevant MCP tools.
4. The tools return results such as image-analysis findings, weather information, or crop guidance.
5. The agent uses those results to prepare a response for the farmer.

AI-generated diagnoses are possibilities, not guaranteed confirmations. Farmers should verify uncertain diagnoses and follow locally appropriate agricultural guidance before applying treatments.

## 🔐 Security

- Keep API keys and secrets in local environment variables.
- Do not upload `.env`, credentials, or private configuration files.
- Exclude virtual environments and generated cache files using `.gitignore`.
- Do not recommend pesticides or chemical treatments without suitable, locally applicable guidance.

## 🧪 Testing

Test the application with different crops, images, symptoms, locations, and languages. Include unclear images and ambiguous symptoms to evaluate how the system handles uncertainty.

## 🎯 Project Goal

The goal of CropGuard is to explore how AI agents, image analysis, weather data, and MCP-based tools can work together to make crop disease assistance more accessible to farmers.

## 👩‍💻 Author

**Khushee Sonagra**

GitHub: [PS-khushee-sonagra](https://github.com/PS-khushee-sonagra)

## 📌 Disclaimer

CropGuard is an AI-assisted informational project. Its output should not replace professional agricultural diagnosis or locally approved crop protection recommendations.