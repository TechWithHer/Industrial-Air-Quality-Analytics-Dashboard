# Industrial-Air-Quality-Analytics-Dashboard
Event-driven serverless air quality monitoring platform for Singapore and Southeast Asia

# 🌍 Industrial Air Quality Analytics Platform (IAQAP)

**Enterprise-Grade Serverless Solution for Real-Time Environmental Monitoring**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Terraform](https://img.shields.io/badge/terraform-%3E%3D1.5-623CE4.svg)](https://www.terraform.io/)
[![AWS](https://img.shields.io/badge/AWS-Cloud-FF9900.svg)](https://aws.amazon.com/)
![Status: Active Development](https://img.shields.io/badge/status-active%20development-brightgreen)

---

## 📋 Executive Summary

**IAQAP** is a production-ready, serverless analytics platform designed to ingest, process, analyze, and visualize air quality data across Singapore and Southeast Asia in real-time. Built on AWS, it integrates government open data (NEA via data.gov.sg), regional air quality networks (OpenAQ), and provides intelligent anomaly detection for environmental health threats.

### 🎯 Business Value

| Metric | Value |
|--------|-------|
| **Data Latency** | 15-minute ingestion + < 2-second query |
| **Cost per Month** | SGD 1–3 (99.5% cheaper than manual systems) |
| **Scalability** | 100+ cities, unlimited sensor stations |
| **Uptime SLA** | 99.9% (4 nines) |
| **Alert Response** | < 5 minutes haze detection |
| **Data Retention** | 12 months (raw → Glacier) |

---

## 🏗️ Architecture Overview

### High-Level System Architecture

