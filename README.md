# Mirumoji Backend

-   **This is the Python (FastAPI) backend service for the [Mirumoji](https://github.com/svdC1/mirumoji_open_front)** application offering tools for Japanese language immersion.
-   What follows is the Setup Guide also available in the [frontend](https://github.com/svdC1/mirumoji_open_front) repo, for more informations you can go there.

# Run Mirumoji Locally with Docker Compose

This guide explains how to run Mirumoji on your local machine using Docker Compose. This setup uses pre-built Docker images for both the frontend and backend services, which will be pulled from GitHub Container Registry (ghcr.io).

## Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Docker and Docker Compose:**
    -   **Windows/macOS:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/). It includes Docker Compose.
    -   **Linux:** Install [Docker Engine](https://docs.docker.com/engine/install/) and then [Docker Compose](https://docs.docker.com/compose/install/).
2.  **For Backend GPU Acceleration:**
    -   **NVIDIA GPU:** You need an NVIDIA graphics card.
    -   **NVIDIA Drivers:** Ensure you have the latest NVIDIA drivers installed for your operating system.
    -   **NVIDIA Container Toolkit:** Install the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html). This allows Docker containers to access your NVIDIA GPU. _If you don't have an NVIDIA GPU, a CPU version allowing access to [MODAL](https://modal.com/) GPU functions using your own credentials is in progress so stay tuned to the next releases._

## Setup Instructions

1.  **Download [`docker-compose.yaml`](https://github.com/svdC1/mirumoji_open_front/docker-compose.yaml):**

    -   Download the `docker-compose.yaml` file from this GitHub release and place it in a new, empty directory on your computer (e.g., `my-app-local`).

2.  **Create an Environment File for the API Key:**

    -   The backend service requires an OpenAI API Key for any GPT-related tasks._If you don't have one you can create it at [OpenAI's API Dshboard](https://platform.openai.com/settings/organization/api-keys)_

    -   In the same directory where you saved `docker-compose.yaml`, create a new file named `.env`.
    -   Open the `.env` file with a text editor and add your OpenAI API key as follows:

        ```env
        OPENAI_API_KEY=your_openai_api_key
        ```

## Running the Application

1.  **Open your terminal or command prompt.**
2.  **Navigate to the directory** where you saved `docker-compose.yaml` and created the `.env` file.
3.  **Start the application by running:**

    ```bash
    docker-compose up -d
    ```

    -   This command will download the necessary Docker images (if you don't have them already), build the containers, and start them in detached mode (`-d`), meaning they will run in the background.
    -   The first time you run this, downloading the images might take a few minutes depending on your internet connection.

## Accessing the Application

Once the containers are running:

-   **Frontend Application:**
    -   Open your web browser and go to you [localhost](http://localhost:4173) at port `4173` where VITE will serve the application in build preview mode.
-   **Backend API (Direct Access):**
    -   The backend API will be accessible at your [localhost](http://localhost:8000) at port `8000` where uvicorn will deploy the API.
    -   The frontend application is configured to communicate with the backend automatically.
    -   If you want to check if the backend is running correctly you can access the [`/health/status`](http://localhost:8000/health/status) endpoint, where you should see the following `JSON` response: `{'status':'ok'}`

## Stopping the Application

To stop the application and remove the containers:

1.  **Open your terminal or command prompt.**
2.  **Navigate to the same directory** where your `docker-compose.yaml` file is located.
3.  **Run the command:**

    ```bash
    docker-compose down
    ```

    -   This command will stop and remove the containers. If you also want to remove the volumes (like the `jamdict_data` and `huggingface_cache` that might store downloaded models/databases to speed up subsequent starts), you can use `docker-compose down -v`.

## Troubleshooting

-   **Port Conflicts:**
    -   If you see errors about ports already being in use (e.g., port `4173` or `8000`), it means another application on your system is using that port. You can either stop the other application or modify the port mappings in the `docker-compose.yaml` file (e.g., change `"4173:4173"` to `"YOUR_NEW_PORT:4173"`).
-   **Docker Not Running:** Ensure the Docker service/daemon is running on your system.
-   **GPU Issues (Backend):** If you encounter issues with the backend and GPU acceleration, double-check your NVIDIA driver installation and that the NVIDIA Container Toolkit is correctly set up. You can check Docker's access to the GPU by running:

```bash
docker run --rm --gpus all nvidia/cuda:12.3.2-base-ubuntu22.04 nvidia-smi
```

---

-   **Enjoy using Mirumoji !**
-   **If you encounter any issues not covered here, please check the main project repository for support or open an issue there.**
