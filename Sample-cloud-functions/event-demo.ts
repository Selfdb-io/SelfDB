// @ts-nocheck
// deno-lint-ignore-file

// Function metadata
export const description = "Demonstrates event-driven functionality";

// Define triggers for this function
export const triggers = [
  // HTTP trigger for manual execution
  {
    type: "http",
    method: ["GET", "POST"]
  },
  // Event trigger - listens for user.created events
  {
    type: "event",
    event: "user.created"
  },
  // Event trigger - listens for message.sent events
  {
    type: "event",
    event: "message.sent"
  }
];

// The function handler
export default async function handler(req, env) {
  console.log("Event demo function executed");
  
  // Get the trigger type from headers
  const triggerType = req.headers?.get("X-Trigger-Type");
  const eventName = req.headers?.get("X-Event-Name");
  
  // If this is an event trigger
  if (triggerType === "event" && eventName) {
    console.log(`Handling event: ${eventName}`);
    
    try {
      // Get the event data
      const eventData = await req.json();
      
      // Process based on event type
      if (eventName === "user.created") {
        return handleUserCreated(eventData);
      } else if (eventName === "message.sent") {
        return handleMessageSent(eventData);
      } else {
        return {
          success: false,
          message: `Unknown event type: ${eventName}`
        };
      }
    } catch (error) {
      console.error("Error processing event:", error);
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  // If this is an HTTP request
  if (req.method === "GET") {
    return {
      success: true,
      message: "Event demo function",
      supportedEvents: ["user.created", "message.sent"],
      usage: "POST to /emit-event with { event: 'user.created', data: { ... } }"
    };
  } else if (req.method === "POST") {
    try {
      // Get the request body
      const body = await req.json();
      
      // Emit an event based on the request
      const eventToEmit = body.event;
      const eventData = body.data || {};
      
      if (!eventToEmit) {
        return {
          success: false,
          message: "Missing 'event' field in request body"
        };
      }
      
      // Return instructions on how to emit the event
      return {
        success: true,
        message: `To emit this event, make a POST request to /emit-event with the following body:`,
        example: {
          event: eventToEmit,
          data: eventData
        }
      };
    } catch (error) {
      return {
        success: false,
        message: "Invalid JSON in request body"
      };
    }
  }
}

// Handler for user.created events
function handleUserCreated(userData) {
  console.log("Processing user.created event:", userData);
  
  // In a real implementation, you might:
  // - Send a welcome email
  // - Set up default preferences
  // - Create related resources
  
  return {
    success: true,
    message: "User created event processed successfully",
    user: userData,
    timestamp: new Date().toISOString()
  };
}

// Handler for message.sent events
function handleMessageSent(messageData) {
  console.log("Processing message.sent event:", messageData);
  
  // In a real implementation, you might:
  // - Send notifications
  // - Update message counters
  // - Process message content
  
  return {
    success: true,
    message: "Message sent event processed successfully",
    messageData: messageData,
    timestamp: new Date().toISOString()
  };
}
