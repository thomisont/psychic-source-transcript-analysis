async function makeOutboundCall(recipientData) {
  try {
    // Use the specified phone number instead of recipient's phone
    let phoneNumber = '2814687449';
    
    // Ensure phone number is in E.164 format for Twilio
    if (!phoneNumber.startsWith('+')) {
      // Add US country code if not present
      phoneNumber = '+1' + phoneNumber;
    }
    
    // Generate a personalized greeting message that includes who is being called
    const message = generatePersonalizedGreeting(recipientData);
    
    // Show calling status in UI
    document.getElementById('calling-status').textContent = `Calling ${phoneNumber} about ${recipientData.name}...`;
    document.getElementById('calling-status').style.display = 'block';
    
    // Make the API call to initiate the outbound call
    const response = await fetch('http://localhost:8001/outbound-call', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        number: phoneNumber,
        first_message: message,
        agent_id: 'hospitality-agent'
      })
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
      // Store the call_sid for ending the call later
      window.currentCallSid = data.call_sid;
      
      // Update UI to show call in progress
      document.getElementById('calling-status').textContent = `Call connected to ${phoneNumber} regarding ${recipientData.name}`;
      
      // Enable end call button
      const endCallButton = document.getElementById('end-call-button');
      if (endCallButton) {
        endCallButton.disabled = false;
        endCallButton.style.display = 'block';
      }
    } else {
      document.getElementById('calling-status').textContent = `Call failed: ${data.message || 'Unknown error'}`;
    }
  } catch (error) {
    console.error('Error making outbound call:', error);
    document.getElementById('calling-status').textContent = `Call failed: ${error.message}`;
  }
}

async function endOutboundCall() {
  try {
    if (!window.currentCallSid) {
      console.error('No active call to end');
      return;
    }
    
    const response = await fetch(`http://localhost:8001/end-call/${window.currentCallSid}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
      document.getElementById('calling-status').textContent = 'Call ended';
      
      // Disable end call button
      const endCallButton = document.getElementById('end-call-button');
      if (endCallButton) {
        endCallButton.disabled = true;
        endCallButton.style.display = 'none';
      }
      
      // Clear the current call SID
      window.currentCallSid = null;
    } else {
      document.getElementById('calling-status').textContent = `Failed to end call: ${data.message || 'Unknown error'}`;
    }
  } catch (error) {
    console.error('Error ending outbound call:', error);
    document.getElementById('calling-status').textContent = `Failed to end call: ${error.message}`;
  }
}

// Helper function to generate a personalized greeting message
function generatePersonalizedGreeting(recipientData) {
  return `Hello, this is the Hotel Concierge calling about guest ${recipientData.name}. We're following up on their recent stay. I hope you're having a great day!`;
} 