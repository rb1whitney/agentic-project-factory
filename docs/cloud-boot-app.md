# Cloud Boot App - Comprehensive Design Document

## 1. Project Overview
The `cloud-boot-app` is a modernized Java Maven Spring Boot 3.2 application designed for secure, cloud-native deployments. Originally based on a classic REST example, this project has been refactored to the latest standards using **Gemini Conductor**, ensuring high-performance runtime, secure containerization, and automated infrastructure management.

## 2. Modernization Strategy (Gemini Conductor Refactor)
The application underwent a comprehensive refactoring process guided by the **Gemini Conductor** protocol. Key improvements include:
- **Runtime Upgrade**: Migrated to **Java 21 (Eclipse Temurin)** for modern language features and performance.
- **Framework Update**: Upgraded to **Spring Boot 3.2.11**, leveraging Jakarta EE namespaces and enhanced observability.
- **Security-First Containerization**: Transitioned to **Google Distroless Java 21** images, significantly reducing the attack surface by removing unnecessary OS binaries.
- **Infrastructure as Code**: Refactored monolithic Terraform into modular, reusable components for AWS.

## 3. Application Architecture

### 3.1 N-Tier Structure
The application follows a standard N-Tier architecture for separation of concerns:
- **Web Layer (`com.dataservice.controller`)**: Exposes RESTful endpoints (`/api/v1/data`) with automated documentation via **Springdoc OpenAPI (Swagger)**.
- **Service Layer (`com.dataservice.service`)**: Orchestrates business logic and decouples the web layer from data persistence.
- **Data Access Layer (`com.dataservice.repository`)**: Implements **Spring Data JPA** for seamless interaction with SQL databases.
- **Domain Layer (`com.dataservice.domain`)**: Defines the core JPA entities and persistence models.

### 3.2 Technology Stack
- **Framework**: Spring Boot 3.2.11
- **Language**: Java 21
- **Build Tool**: Maven 3.9+
- **Database**: H2 (In-memory for Dev/Test), MySQL (Production)
- **APIs**: REST (JSON/XML)
- **Testing**: JUnit 5 (Jupiter)
- **Containerization**: Podman/Docker with Distroless Java 21 (Debian 12)

## 4. Infrastructure Architecture (Terraform, Helm, & Crossplane)

The infrastructure follows a multi-layered deployment strategy combining the strengths of Terraform, Helm, and Crossplane.

### 4.1 Core Infrastructure (Terraform)
Managed under `cloud-boot-app/terraform/core/`, these resources represent the foundation required for the application to function in a production-like environment:
- **Data Persistence**: A managed **RDS MySQL 8.0** instance (db.t3.micro) for reliable data storage.
- **Object Storage**: An **S3 Bucket** configured with restrictive public access blocks for application assets.
- **Security & IAM**: Dedicated Security Groups for database isolation and an **IAM Role with IRSA** (IAM Roles for Service Accounts) to grant the containerized app secure access to S3 without static credentials.

### 4.2 Application Orchestration (Helm)
A standard Helm v3 chart (in `cloud-boot-app/helm/`) is used to package the Kubernetes workload:
- **Scalable Deployment**: Manages application replicas with built-in health checks.
- **Service Management**: Configurable `Service` and `Ingress` templates.
- **Security Context**: Optimized for Google Distroless Java 21 images.

### 4.3 GitOps & Managed Deployment (Crossplane v2)
For automated lifecycle management within Kubernetes, **Crossplane** is used as the control plane following the "v2" Composite Resource model:

- **Composite Resource Definition (XRD)**: Defines a high-level **`CloudBootApp`** resource in `cloud-boot-app/crossplane/apis/`, abstracting away the underlying AWS and Helm complexities.
- **V2-Style Composition**: The implementation (`cloud-boot-app/crossplane/compositions/`) bundles multiple managed resources (RDS, S3, and Helm Release) into a single logical unit.
- **Environment Scaffolding (EnvironmentConfigs)**: 
  - Just like Terraform's `.tfvars`, Crossplane uses **`EnvironmentConfigs`** in `cloud-boot-app/crossplane/environments/` to manage environment-specific data.
  - This allows the same `Composition` to dynamically provision a `db.t3.micro` for **Dev** and a `db.m5.large` for **Production** based on the environment label in the Claim.
- **Unified Interface**: Developers interact only with the `CloudBootApp` Claim, enabling a self-service model for provisioning both cloud infrastructure and application workloads.


### 4.3 Policy Enforcement (Gatekeeper/OPA)
To ensure the security posture of the application, a set of **Gatekeeper** policies is provided in `cloud-boot-app/gatekeeper/`:
- **Privileged Container Restriction**: Prevents the use of privileged containers in the `cloud-boot-app` namespace.
- **Read-Only Root Filesystem Enforcement**: Forces the root filesystem to be read-only, preventing runtime modifications to the container's base image. The Helm chart is pre-configured to mount an `emptyDir` at `/tmp` to support Spring Boot's requirements while remaining compliant.
- **Admission Control**: Policies are applied at the cluster admission stage, ensuring no non-compliant resources can be deployed.

## 5. CI/CD & Operations
- **Jenkins**: Uses a modernized Dockerfile with Java 21 for build consistency.
- **Travis CI**: Integrated for automated pull request validation.
- **Vagrant**: Updated to Ubuntu 22.04 for local development environment parity.
- **Observability**: Integrated with **Spring Boot Actuator** for health monitoring and metrics.

## 6. Developer Guide

### Local Development
```bash
# Default (H2)
mvn spring-boot:run

# MySQL Profile
mvn spring-boot:run -Dspring-boot.run.profiles=mysql
```

### Containerized Deployment
```bash
# Build
podman build -t cloud-boot-app:modernized .

# Run
podman run -p 8090:8090 -d cloud-boot-app:modernized
```

---
*Author: Richard Whitney*
*Created as part of the Cloud Boot App modernization.*
