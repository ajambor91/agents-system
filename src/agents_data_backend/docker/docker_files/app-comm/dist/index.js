"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const axios_1 = __importDefault(require("axios"));
const express_1 = __importDefault(require("express"));
const redis_1 = require("redis");
const uuid_1 = require("uuid");
const zod_1 = require("zod");
const port = Number(process.env.PORT || 3001);
const appDataUrl = (process.env.APP_DATA_URL || 'http://localhost:3000').replace(/\/$/, '');
const redisUrl = process.env.REDIS_STREAM_URL || 'redis://localhost:6380';
const app = (0, express_1.default)();
const streams = (0, redis_1.createClient)({ url: redisUrl });
app.use(express_1.default.json({ limit: '1mb' }));
const messageItemSchema = zod_1.z.object({
    type: zod_1.z.enum(['question', 'info']),
    content: zod_1.z.string().min(1).max(100_000),
}).strict();
const payloadSchema = zod_1.z.object({
    sender: zod_1.z.string().trim().min(1).max(128),
    date: zod_1.z.string().datetime(),
    receivers: zod_1.z.array(zod_1.z.string().trim().min(1).max(128)).min(1).max(100),
    messages: zod_1.z.array(messageItemSchema).min(1).max(100),
}).strict();
streams.on('error', (error) => console.error('[app-comm] Redis error', error));
app.get('/health', (_request, response) => {
    response.json({
        status: streams.isReady ? 'ok' : 'degraded',
        service: 'app-comm',
        streams: streams.isReady,
    });
});
app.post('/api/messages', async (request, response) => {
    try {
        const parsed = payloadSchema.parse(request.body);
        const receivers = [...new Set(parsed.receivers)];
        const messageId = (0, uuid_1.v4)();
        const storedMessage = {
            id: messageId,
            seenBy: [],
            archived: false,
            createdAt: new Date().toISOString(),
            content: { ...parsed, receivers },
        };
        // Persist first. A stream event must never point to a message that app-data
        // cannot return to the receiver.
        await axios_1.default.post(`${appDataUrl}/api/internal/messages`, storedMessage, {
            timeout: 10_000,
            headers: { 'Content-Type': 'application/json' },
        });
        await Promise.all(receivers.map((receiver) => streams.xAdd(`stream:${receiver}`, '*', { action: 'NEW_MESSAGE', messageId, sender: parsed.sender })));
        response.status(202).json({
            success: true,
            messageId,
            status: 'persisted_and_published',
        });
    }
    catch (error) {
        if (error instanceof zod_1.z.ZodError) {
            response.status(400).json({ error: 'validation_failed', details: error.errors });
            return;
        }
        if (axios_1.default.isAxiosError(error)) {
            console.error('[app-comm] app-data failure', error.message);
            response.status(503).json({ error: 'app_data_unavailable' });
            return;
        }
        console.error('[app-comm] send failure', error);
        response.status(500).json({ error: 'internal_error' });
    }
});
async function start() {
    await streams.connect();
    app.listen(port, () => console.log(`[app-comm] listening on ${port}`));
}
async function shutdown() {
    if (streams.isOpen) {
        await streams.quit();
    }
    process.exit(0);
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
start().catch((error) => {
    console.error('[app-comm] startup failed', error);
    process.exit(1);
});
