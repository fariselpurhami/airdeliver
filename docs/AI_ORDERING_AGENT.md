# AI Ordering Agent Documentation

This document outlines the architecture and customization points for the airdeliver AI Ordering Agent.

## Architecture

The system consists of three main parts:
1.  **Frontend UI (`AIOrderingOverlay.tsx`)**: A global React component that provides the chat interface.
2.  **Frontend Logic (`useAIOrdering.ts`)**: A React hook that manages the conversation state and communicates with the backend.
3.  **Backend API (`/api/v1/ai-ordering`)**: A FastAPI endpoint that receives user messages.
4.  **Backend Service (`ai_ordering_service.py`)**: A service that contains the core logic for parsing intent and orchestrating the ordering workflow.

## Customizing the AI

### Intent Parsing
The current intent parsing is a simulation located in `ai_ordering_service.py` in the `_parse_intent` method. It uses regular expressions to detect user goals.

To add a new intent (e.g., "remove item"):
1.  Add a new regular expression to the `_parse_intent` method.
2.  Add a new `if intent == "NEW_INTENT":` block to the `handle_message` method.
3.  Implement the business logic for the new intent.

### AI Retraining (Future)
For a production system, the simulated NLU should be replaced with a real NLU service (like Rasa, Google Dialogflow, or a custom spaCy/transformer model). The `_parse_intent` method is the designated point of integration.

The retraining lifecycle would involve:
1.  Logging anonymized user queries and their outcomes.
2.  Periodically using these logs to fine-tune the NLU model.
3.  Deploying the updated model and routing traffic to it via a feature flag.
