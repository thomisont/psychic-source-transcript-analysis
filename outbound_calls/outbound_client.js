/**
 * Client for interacting with the outbound call service
 */

const OUTBOUND_SERVICE_URL = process.env.OUTBOUND_SERVICE_URL || 'http://localhost:8001';

/**
 * Makes an outbound call to the specified phone number with the given message
 * 
 * @param {string} phoneNumber - The phone number to call
 * @param {string} message - The message to be spoken during the call
 * @returns {Promise<Object>} - Response with status and conversation ID
 */
async function makeOutboundCall(phoneNumber, message) {
  try {
    console.log(`Initiating outbound call to ${phoneNumber}`);
    
    const response = await fetch(`${OUTBOUND_SERVICE_URL}/outbound-call`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        phone_number: phoneNumber,
        message: message,
      }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`Failed to make outbound call: ${errorData.detail || response.statusText}`);
    }
    
    const data = await response.json();
    console.log('Outbound call initiated successfully:', data);
    return data;
  } catch (error) {
    console.error('Error in outbound call client:', error);
    throw error;
  }
}

/**
 * Checks the health of the outbound call service
 * 
 * @returns {Promise<boolean>} - Whether the service is healthy
 */
async function checkOutboundServiceHealth() {
  try {
    const response = await fetch(`${OUTBOUND_SERVICE_URL}/health`);
    
    if (!response.ok) {
      return false;
    }
    
    const data = await response.json();
    return data.status === 'healthy';
  } catch (error) {
    console.error('Error checking outbound service health:', error);
    return false;
  }
}

module.exports = {
  makeOutboundCall,
  checkOutboundServiceHealth,
}; 