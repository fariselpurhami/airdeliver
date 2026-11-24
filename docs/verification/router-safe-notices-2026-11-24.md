# Router safe cause classes and schema contract

Owner logs show Groq200 followed by router.schema_violation ValidationError.
This establishes schema rejection, not missingTavily/key/ratequota. The oldgeneric
notice hid this distinction. Safe notices now distinguish authentication,429limit,
provider5xx/requestconfiguration,timeout,connection,invalidschema and generic
unvalidatedresult.429does not establish creditexhaustion vs requestlimit.
No rawprovidererror,response,prompt,key,URLoraccountdetails in notices/logs.

The exact generated RouterDecision JSONschema accompanies the routingpolicy,
reducing hand-written contractdrift. No relaxed enum/action/type acceptance.
Schemafailure logs only schema-owned fieldlocations and fixedvalidatorerrorcodes,
not values/messages/context. This permits the exact failingfield to be diagnosed
without logging customer/modelcontent. The actual failedownerpayload is unavailable,
so its precise shape is not asserted or guessed. A valid exactspecificationquestion
payload passes actualschema; nullwrongtypes reject with safefielddiagnostics.
Realprovidercompliance remains unverified until ownerretest/logs.
