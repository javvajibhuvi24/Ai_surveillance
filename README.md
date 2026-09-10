# 🛡️ Enterprise AI Surveillance System

An AI-powered real-time surveillance platform built with **Python, Flask, OpenCV, YOLO, and DeepFace** for intelligent monitoring, safety compliance, person detection, and automated incident management.

## 🚀 Overview

The **Enterprise AI Surveillance System** combines computer vision, deep learning, face analysis, and web technologies to transform traditional camera monitoring into an intelligent surveillance workflow.

The system can analyze live camera streams, detect people and safety-related objects, process surveillance events, maintain incident records, and provide a web-based monitoring interface.

### Core Pipeline

```text
Camera / Video Feed
        ↓
   OpenCV Processing
        ↓
 YOLO Object Detection
        ↓
 Face / Safety Analysis
        ↓
 Event & Compliance Detection
        ↓
 Alert Generation
        ↓
 Incident Logging
        ↓
 Flask Web Dashboard
```

---

## ✨ Features

### 🎥 Real-Time Surveillance

* Live camera/video stream processing
* OpenCV-based frame processing
* Real-time AI inference
* Web-based monitoring interface

### 🤖 AI Object Detection

* YOLO-based object detection
* PPE detection
* Person detection
* Custom-trained detection models
* Configurable detection pipeline

### 👤 Face Analysis

* Face detection and recognition workflow
* DeepFace integration
* Authorized-person verification
* Configurable face-processing engine

### 🚨 Intelligent Alerts

* Automated surveillance alerts
* Safety/compliance violation detection
* Incident event processing
* Notification integration

### 📋 Incident Management

* Incident history
* Event logging
* Timestamped surveillance events
* Historical incident review

### 🌐 Web Dashboard

* Flask-powered web application
* Live monitoring interface
* Login interface
* Incident history page
* Responsive frontend

---

## 🧠 AI & Machine Learning

The project uses several AI/computer-vision technologies:

| Technology         | Purpose                            |
| ------------------ | ---------------------------------- |
| YOLO / Ultralytics | Object detection                   |
| OpenCV             | Computer vision & video processing |
| DeepFace           | Face analysis                      |
| Python             | AI application development         |
| NumPy              | Numerical processing               |
| Pillow             | Image processing                   |

---

## 🏗️ Project Structure

```text
enterprise-ai-surveillance/
│
├── app.py
├── alerts.py
├── check_model.py
├── compliance.py
├── config.py
├── diagnose.py
├── diagnose_model.py
├── download_ppe_model.py
├── face_engine.py
├── network_utils.py
├── ppe_detector.py
├── stream_handler.py
│
├── test_face.py
├── test_models.py
├── train_combined.py
├── train_ppe.py
├── telegram_test.py
│
├── requirements.txt
│
├── templates/
│   ├── index.html
│   ├── login.html
│   └── history.html
│
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/javvajibhuvi24/Ai_surveillance.git
cd Ai_surveillance
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Configuration

Create a `.env` file for private configuration and credentials.

Example:

```env
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

**Never commit `.env` or API credentials to GitHub.**

---

## ▶️ Running the Application

After installing the dependencies:

```bash
python app.py
```

The Flask application will start locally.

Open the displayed local address in your browser.

---

## 🧪 Testing

The repository contains several testing and diagnostic scripts:

```bash
python test_models.py
```

```bash
python test_face.py
```

Additional diagnostic scripts are available for troubleshooting model and application configuration.

---

## 📊 Current System Capabilities

The current implementation provides the foundation for an intelligent enterprise surveillance platform, including:

* Real-time video processing
* AI-based object detection
* PPE detection
* Face analysis
* Compliance monitoring
* Automated alerts
* Incident logging
* Flask dashboard

---

## 🔮 Future Improvements

Planned improvements include:

* [ ] Multi-camera management
* [ ] Real-time WebSocket alerts
* [ ] Advanced person tracking
* [ ] Improved anomaly detection
* [ ] Automated incident video recording
* [ ] Analytics and visualization dashboard
* [ ] Role-based authentication
* [ ] Database-backed incident management
* [ ] Cloud deployment
* [ ] Containerized deployment with Docker
* [ ] Production-grade API architecture
* [ ] Model performance monitoring
* [ ] Automated notification workflows

---

## 🛠️ Tech Stack

**Programming**

* Python
* JavaScript
* HTML
* CSS

**AI / Computer Vision**

* YOLO
* Ultralytics
* OpenCV
* DeepFace
* NumPy
* Pillow

**Backend**

* Flask

**Development**

* Git
* GitHub
* Python Virtual Environment

---

## 🎯 Project Objective

The goal of this project is to build an intelligent surveillance platform that can assist organizations in monitoring environments, identifying safety-related events, and reducing the limitations of manual surveillance.

The project demonstrates practical application of:

**Computer Vision + Deep Learning + AI Automation + Web Engineering**

---

## 👩‍💻 Author

### Javvaji Bhuvi

**AI Engineer | Machine Learning | Generative AI | Computer Vision**

Computer Science student focused on building practical AI systems and intelligent applications.

### Connect

* [LinkedIn](https://www.linkedin.com/in/javvaji-bhuvi)
* [GitHub](https://github.com/javvajibhuvi24)

---

## 📄 License

This project is intended for educational, research, and portfolio purposes.
