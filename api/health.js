export default function handler(req, res) {
  res.status(200).json({
    status: "ok",
    service: "NovaResolve Cloud Platform",
    deployment: "Vercel Serverless",
    timestamp: new Date().toISOString()
  });
}
