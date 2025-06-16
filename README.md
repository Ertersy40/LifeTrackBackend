# LifeTrackBackend
[![Ask DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/Ertersy40/LifeTrackBackend)

LifeTrackBackend is a Python-based backend service designed to power an automated personal tracking and check-in system, potentially named "Dialogger" or "LifeTrack." It utilizes phone calls (via the Vapi API) and AI-driven transcription analysis (OpenAI GPT-4) to onboard users, help them define trackable goals/habits, and conduct regular check-in calls to update their progress. All user data, graph configurations, and progress are stored in a Supabase database.

## Features

*   **Automated User Onboarding:** Initiates a phone call to new users to gather their name, basic information, and identify goals or habits they wish to track.
*   **AI-Powered Conversation Analysis:** Parses transcriptions of phone calls to:
    *   Extract user-defined goals and suggest appropriate graph types (heatmap, line, bar).
    *   Create and update a user profile with personal details and preferences.
    *   Log daily/regular progress on their chosen metrics.
    *   Determine the user's preferred time for subsequent check-in calls.
*   **Scheduled Check-in Calls:** Automatically makes follow-up calls at user-specified times to collect updates on their tracked activities.
*   **Dynamic Graph Generation:** Creates configurations for various graph types based on user goals.
*   **Data Persistence:** Securely stores all user information, graph settings, and tracked data points in Supabase.
*   **Webhook Integration:** Handles real-time events from the Vapi calling service (e.g., call started, call ended, transcription ready).

## Core Components

*   **`main.py`**: The main FastAPI application. Defines API endpoints for:
    *   `/webhook`: Receives and processes events from the Vapi call service (e.g., end-of-call reports, status updates).
    *   `/onboarding`: Triggers the onboarding call sequence for new users.
    *   `/task`: Initiates a check-in call for an existing user.
*   **`makeCall.py`**: Manages interactions with the Vapi API to make outbound phone calls. It constructs dynamic prompts for both onboarding and task check-in calls.
*   **`transcriptionAnalysis.py`**: Contains the core logic for interacting with the OpenAI API (GPT-4). It processes call transcriptions to:
    *   `generateGraphObjects()`: Identifies goals and sets up graph configurations.
    *   `getInitialUserObject()`: Creates the initial user profile.
    *   `UpdateGraphs()`: Updates graph data with new entries.
    *   `updateUserData()`: Modifies the user's profile based on new information.
    *   `setNextCall()`: Determines the time for the next scheduled call.
*   **`graphs.py`**: Handles the creation of graph configurations in the Supabase database and seeds initial data.
*   **`helper.py`**: Provides utility functions for various tasks, including:
    *   Supabase database operations (CRUD for user data, call status, graph data).
    *   Formatting conversation transcripts.
    *   Converting timestamps between ISO 8601 UTC and GMT+10 local time.
    *   Retrieving Vapi phone number IDs based on country codes.
*   **`supabaseClient.py`**: Initializes and configures the Supabase client for database communication.
*   **`requirements.txt`**: Lists all Python package dependencies for the project.

## Environment Variables

For the application to run correctly, the following environment variables must be set:
*   `VAPI_API_KEY`: Your API key for the Vapi service.
*   `VAPI_US_PHONE_ID`: Vapi Phone Number ID for US calls.
*   `VAPI_AU_PHONE_ID`: Vapi Phone Number ID for Australian calls.
*   `VAPI_NZ_PHONE_ID`: Vapi Phone Number ID for New Zealand calls.
*   `VAPI_UK_PHONE_ID`: Vapi Phone Number ID for UK calls.
*   `SERVER_URL`: The publicly accessible base URL of this backend server (used for Vapi webhooks, e.g., `https://your-backend-url.com`).
*   `SUPABASE_URL`: The URL of your Supabase project.
*   `SUPABASE_SERVICE_ROLE_KEY`: The service role key for your Supabase project (allows admin-level access).
*   `MY_OPENAI_KEY`: Your API key for OpenAI.

It's recommended to use a `.env` file to manage these variables locally.

## Setup and Running

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ertersy40/lifetrackbackend.git
    cd lifetrackbackend
    ```
2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up environment variables:**
    Create a `.env` file in the root directory of the project and add the necessary environment variables listed above.
    Example `.env` file:
    ```env
    VAPI_API_KEY="your_vapi_key"
    VAPI_US_PHONE_ID="your_vapi_us_phone_id"
    # ... other VAPI phone IDs
    SERVER_URL="https://your-server.com"
    SUPABASE_URL="https://your-project.supabase.co"
    SUPABASE_SERVICE_ROLE_KEY="your_supabase_service_role_key"
    MY_OPENAI_KEY="your_openai_key"
    ```
5.  **Run the FastAPI application:**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```
    The application will be accessible at `http://localhost:8000`.

## API Endpoints

*   **`POST /webhook`**:
    *   **Description**: Endpoint for Vapi to send call-related events (e.g., `end-of-call-report`, `status-update`).
    *   **Payload**: Varies based on the Vapi event type.
    *   **Functionality**: Processes call transcriptions, updates call statuses, triggers data analysis, and schedules next steps.
*   **`POST /onboarding`**:
    *   **Description**: Initiates an onboarding call to a new user.
    *   **Request Body**:
        ```json
        {
            "phone_number": "string" // User's phone number
        }
        ```
    *   **Response**: Returns the call SID if successful, or an error message.
    *   **Functionality**: Creates user records in Supabase and triggers an onboarding call via Vapi. Checks if user is already onboarded.
*   **`POST /task`**:
    *   **Description**: Initiates a task check-in call for an existing user.
    *   **Request Body**:
        ```json
        {
            "userId": "string" // User's unique ID
        }
        ```
    *   **Functionality**: Retrieves user data and current graph information, then triggers a task check-in call via Vapi.
