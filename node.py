from typing import Dict, Any

# Type alias for clarity
NodeConfig = Dict[str, Any]

# Function Handlers
def collect_user_info(name: str, age: int):
    return {"name": name, "age": age}

def handle_user_info(user_info: Dict[str, Any]):
    """ Transition from collecting user info to asking about relationship preferences """
    user_name = user_info.get("name", "there")
    print(f"User info collected: {user_info}")

    # Move to the next node (preferences)
    return {
        "next_node": create_preferences_node(user_name),
        "response": f"Nice to meet you, {user_name}! Now, let's talk about what you're looking for in a partner."
    }

def collect_relationship_preferences(interests: str, partner_criteria: Dict[str, str]):
    return {"interests": interests, "partner_criteria": partner_criteria}

def handle_relationship_preferences(preferences: Dict[str, Any]):
    """ Transition from collecting relationship preferences to providing advice """
    print(f"Relationship preferences collected: {preferences}")

    # Move to the next node (advice)
    user_name = preferences.get("name", "there")
    age = preferences.get("age", 0)  # Assume age was collected earlier

    return {
        "next_node": create_advice_node(user_name, age),
        "response": f"Thanks for sharing your preferences, {user_name}. Now, let's talk about some relationship advice."
    }

def provide_advice(age: int, relationship_status: str):
    return {"advice": f"Based on your age {age} and status {relationship_status}, here is some advice..."}

def handle_advice(advice: Dict[str, Any]):
    """ Final step: End or update preferences """
    print(f"Advice provided: {advice}")

    return {
        "response": "I hope that advice was helpful! Would you like to adjust any preferences or end the session?",
        "next_node": create_update_or_end_node()
    }

def update_preferences(interests: str, partner_criteria: Dict[str, str]):
    return {"updated_interests": interests, "updated_criteria": partner_criteria}

def handle_update_preferences(updated_preferences: Dict[str, Any]):
    print(f"Preferences updated: {updated_preferences}")

    return {
        "response": "Your preferences have been updated. Let me know if you need anything else!",
        "next_node": create_advice_node(updated_preferences.get("name", "there"), updated_preferences.get("age", 0))
    }

def end_session():
    return {"status": "completed"}

def handle_end_session(end_status: Dict[str, Any]):
    print(f"Session ended: {end_status}")

# Node configurations
def create_initial_node() -> NodeConfig:
    return {
        "role_messages": [
            {
                "role": "system",
                "content": "You are a relationship counselor. Always wait for user responses before calling functions."
            }
        ],
        "task_messages": [
            {
                "role": "assistant",
                "content": "Hello! I'm your relationship counselor. Let's start by getting to know each other. What is your name and age?"
            }
        ],
        "functions": [
            {
                "function_declarations": [
                    {
                        "name": "collect_user_info",
                        "handler": collect_user_info,
                        "description": "Record user's name and age.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "age": {"type": "integer"},
                            },
                            "required": ["name", "age"],
                        },
                        "transition_callback": handle_user_info,
                    }
                ]
            }
        ],
    }

def create_preferences_node(user_name: str) -> NodeConfig:
    return {
        "task_messages": [
            {
                "role": "assistant",
                "content": f"Nice to meet you, {user_name}! Let's talk about what you're looking for in a partner."
            }
        ],
        "functions": [
            {
                "function_declarations": [
                    {
                        "name": "collect_relationship_preferences",
                        "handler": collect_relationship_preferences,
                        "description": "Gather user's relationship preferences.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "interests": {"type": "string"},
                                "partner_criteria": {
                                    "type": "object",
                                    "properties": {
                                        "age_range": {"type": "string"},
                                        "height": {"type": "string"},
                                        "financial_goals": {"type": "string"},
                                        "values": {"type": "string"},
                                    },
                                    "required": ["age_range", "height", "financial_goals", "values"]
                                },
                            },
                            "required": ["interests", "partner_criteria"],
                        },
                        "transition_callback": handle_relationship_preferences,
                    }
                ]
            }
        ],
    }

def create_advice_node(user_name: str, age: int) -> NodeConfig:
    return {
        "task_messages": [
            {
                "role": "assistant",
                "content": f"Thanks, {user_name}. Based on your preferences, I have some relationship advice for you."
            }
        ],
        "functions": [
            {
                "function_declarations": [
                    {
                        "name": "provide_advice",
                        "handler": provide_advice,
                        "description": "Offer relationship advice.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "age": {"type": "integer"},
                                "relationship_status": {"type": "string", "enum": ["single", "divorced"]},
                            },
                            "required": ["age", "relationship_status"],
                        },
                        "transition_callback": handle_advice,
                    }
                ]
            }
        ],
    }

def create_update_or_end_node() -> NodeConfig:
    return {
        "task_messages": [
            {
                "role": "assistant",
                "content": "Would you like to adjust any of your preferences, or are you satisfied with our session?"
            }
        ],
        "functions": [
            {
                "function_declarations": [
                    {
                        "name": "update_preferences",
                        "handler": update_preferences,
                        "description": "Allow users to update their relationship preferences.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "interests": {"type": "string"},
                                "partner_criteria": {
                                    "type": "object",
                                    "properties": {
                                        "age_range": {"type": "string"},
                                        "height": {"type": "string"},
                                        "financial_goals": {"type": "string"},
                                        "values": {"type": "string"},
                                    },
                                    "required": ["age_range", "height", "financial_goals", "values"]
                                },
                            },
                            "required": ["interests", "partner_criteria"],
                        },
                        "transition_callback": handle_update_preferences,
                    },
                    {
                        "name": "end_session",
                        "handler": end_session,
                        "description": "End the relationship counseling session.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string", "enum": ["completed"]},
                            },
                            "required": ["status"],
                        },
                        "transition_callback": handle_end_session,
                    }
                ]
            }
        ],
    }
