# TDS-Project-LLM-Code-Deployment
An intelligent deployment API that transforms a simple brief into a live, hosted web application using AI. Built with FastAPI, it automates the entire workflow from LLM-powered code generation to deployment on GitHub Pages, handling multi-round updates and robust error handling.

# 🚀 AI-Powered Deployment API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

An intelligent deployment-as-a-service API that transforms a simple text brief into a fully functional, live web application. It leverages a Large Language Model (LLM) to generate code and automates the entire deployment pipeline to GitHub Pages, handling multi-round updates and providing robust feedback mechanisms.

## 📖 Overview

This project was designed to solve the challenge of rapidly prototyping and deploying simple web applications. Instead of manually writing code, setting up a repository, and configuring hosting, you simply send a single `POST` request with a description of your desired app. The API handles the rest:

1.  **Generates** the application code using an LLM.
2.  **Creates** a new, public GitHub repository.
3.  **Pushes** the generated code, a professional `README.md`, and an `MIT` license.
4.  **Enables** GitHub Pages for live deployment.
5.  **Notifies** the requesting service with the final repository and pages URLs.

It's a complete, end-to-end solution for automated web application lifecycle management.

## 🏗️ Architecture

The system follows a modular, event-driven architecture to ensure reliability and scalability.

## ✨ Key Features
- ✨ AI-Driven Code Generation: Uses a powerful LLM to generate clean, functional HTML/CSS/JavaScript from a simple text brief.
- 🚀 Automated Deployment: Fully manages the GitHub repository lifecycle, from creation to pushing files and enabling Pages.
- 🔄 Multi-Round Support: Handles iterative development by accepting update requests (round: 2) to modify and redeploy applications.
- 🛡️ Secure & Robust: Validates requests via a shared secret and implements an exponential backoff retry mechanism for all critical API calls.
- 📊 Full Logging & Callbacks: Provides detailed console logs and pings a callback URL with deployment metadata (repo_url, commit_sha, pages_url) upon completion.
- 📄 Professional Repo Generation: Automatically creates a standard MIT LICENSE and a comprehensive README.md for every generated project.


## 📄 License
This project is licensed under the MIT License. See the LICENSE file for details.
