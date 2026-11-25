// Check gateway and Next static serving without initiating a page compilation.
try {
 const response=await fetch('http://127.0.0.1:3000/logo.png',{
  signal:AbortSignal.timeout(5000),redirect:'error',
 });
 await response.body?.cancel();
 process.exit(response.ok?0:1);
} catch { process.exit(1); }
