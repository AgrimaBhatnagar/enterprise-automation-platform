# Enterprise Automation Platform

## Overview

A role-based infrastructure automation system that enables users to request virtual machines and admins to approve provisioning using Terraform and Ansible.

## Features

* Role-Based Access Control (Admin/User)
* VM provisioning using Terraform (GCP)
* Configuration using Ansible
* Asynchronous execution (background threads)
* Retry logic for reliability
* Structured logging for observability
* CI/CD pipeline using GitHub Actions

## Architecture

User → Request VM → Admin Approval → Async Worker → Terraform → Ansible → Logs

## Tech Stack

* Flask
* SQLAlchemy
* Terraform
* Ansible
* GitHub Actions
* GCP

## Key Learnings

* Designed async job workflow (pending → approved → running → completed)
* Implemented retry + failure handling
* Built infra automation pipeline end-to-end
