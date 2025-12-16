// functions/incoming-call.js
const { createClient } = require('@supabase/supabase-js');

exports.handler = async function(context, event, callback) {
  const twiml = new Twilio.twiml.VoiceResponse();
  const supabase = createClient(context.SUPABASE_URL, context.SUPABASE_KEY);
  const callerPhone = event.From;
  console.log(`Incoming call from: ${callerPhone}`);

  try {
    let { data: users, error } = await supabase
      .from('user_profiles')
      .select('full_name, parent_name, current_prompt')
      .eq('parent_phone', callerPhone)
      .limit(1);

    if (error) throw error;

    if (users && users.length > 0) {
      // ✅ KNOWN USER
      const user = users[0];
      const parentName = user.parent_name || "Mom";
      const topic = user.current_prompt || "tell me about your day.";
      
      // 1. Greeting (Amy / British / Formal)
      twiml.say({ 
          voice: 'Polly.Amy-Neural', 
          language: 'en-GB' 
        }, 
        `Greetings from Nashville, ${parentName}. We are ready for your story.`);
        
      twiml.pause({ length: 1 });
      
      // 2. Topic
      twiml.say({ 
          voice: 'Polly.Amy-Neural', 
          language: 'en-GB' 
        }, 
        `Here is this week's topic: ${topic}`);
        
      twiml.pause({ length: 1 });
      
      // 3. Instruction
      twiml.say({ 
          voice: 'Polly.Amy-Neural', 
          language: 'en-GB' 
        }, 
        "Please start speaking after the beep. Press hash when finished.");
      
    } else {
      // UNKNOWN CALLER
      twiml.say({ 
          voice: 'Polly.Amy-Neural', 
          language: 'en-GB' 
        }, 
        "Welcome to the Family Archive. We didn't recognize this number, but you can still record a story.");
    }

    twiml.record({ maxLength: 3600, finishOnKey: '#' });

  } catch (err) {
    console.error(err);
    twiml.say("Sorry, we had a database connection error.");
  }

  return callback(null, twiml);
};
