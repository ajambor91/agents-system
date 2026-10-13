import express from 'express';

const app = express();
const port = Number(process.env.PORT || 3002);

app.use(express.json({ limit: '1mb' }));

app.get('/health', (_request, response) => {
  response.json({ status: 'ok', service: 'app-sync' });
});

// app-sync intentionally owns synchronization with the future local sync tool.
// Message delivery and persistence do not depend on this endpoint.
app.get('/api/sync/status', (_request, response) => {
  response.json({ status: 'idle', service: 'app-sync' });
});

app.listen(port, () => {
  console.log(`[app-sync] listening on ${port}`);
});
