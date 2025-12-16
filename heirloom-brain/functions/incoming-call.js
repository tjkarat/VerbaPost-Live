// functions/incoming-call.js
const { createClient } = require('@supabase/supabase-js');

exports.handler = async function(context, event, callback) {
  const twiml = new Twilio.twiml.VoiceResponse();
  const supabase = createClient(context.SUPABASE_URL, context.SUPABASE_KEY);
  const callerPhone = event.From;
  console.log(`Incoming call from: ${callerPhone}`);

  try {
    // 1. Look up the caller in your database
    let { data: users, error } = await supabase
      .from('user_profiles')
      .select('full_name, parent_name, current_prompt')
      .eq('parent_phone', callerPhone)
      .limit(1);

    if (error) throw error;

    if (users && users.length > 0) {
      // ✅ KNOWN USER: Greeting by Name + Custom Topic
      const user = users[0];
      const parentName = user.parent_name || "Mom";
      const topic = user.current_prompt || "tell me about your day.";
      
      twiml.say({ voice: 'polly.joanna-neural' }, 
        `Hi ${parentName}. We are ready for your story.`);
      twiml.pause({ length: 1 });
      
      twiml.say({ voice: 'polly.joanna-neural' }, 
        `Here is this week's topic: ${topic}`);
      twiml.pause({ length: 1 });
      
      twiml.say("Please start speaking after the beep. Press hash when finished.");
      
    } else {
      // ❌ UNKNOWN CALLER: Generic Greeting
      twiml.say("Welcome to the Family Archive. We didn't recognize this number, but you can still record a story.");
    }

    // 2. Record the Audio
    twiml.record({ maxLength: 3600, finishOnKey: '#' });

  } catch (err) {
    console.error(err);
    twiml.say("Sorry, we had a database connection error.");
  }

  return callback(null, twiml);
};
