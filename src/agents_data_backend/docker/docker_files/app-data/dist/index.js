"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const mongoose_1 = __importDefault(require("mongoose"));
const redis_1 = require("redis");
const port = Number(process.env.PORT || 3000);
const mongoUrl = process.env.MONGO_URL || 'mongodb://localhost:27017/appdb';
const cacheUrl = process.env.REDIS_CACHE_URL || 'redis://localhost:6379';
const cacheTtl = Number(process.env.MESSAGE_CACHE_TTL_SECONDS || 604800);
const app = (0, express_1.default)();
const cache = (0, redis_1.createClient)({ url: cacheUrl });
const messageSchema = new mongoose_1.default.Schema({
    id: { type: String, required: true, unique: true, index: true },
    seenBy: { type: [String], default: [] },
    archived: { type: Boolean, default: false },
    createdAt: { type: String, required: true },
    content: { type: mongoose_1.default.Schema.Types.Mixed, required: true },
}, { versionKey: false });
const Message = mongoose_1.default.model('Message', messageSchema);
cache.on('error', (error) => console.error('[app-data] Redis cache error', error));
app.use(express_1.default.json({ limit: '1mb' }));
function isRecord(value) {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function validateMessage(value) {
    if (!isRecord(value))
        return null;
    if (typeof value.id !== 'string' || !value.id)
        return null;
    if (!Array.isArray(value.seenBy) || !value.seenBy.every((item) => typeof item === 'string'))
        return null;
    if (typeof value.archived !== 'boolean')
        return null;
    if (typeof value.createdAt !== 'string' || !value.createdAt)
        return null;
    if (!isRecord(value.content))
        return null;
    return value;
}
function cacheKey(messageId) {
    return `message:${messageId}`;
}
app.get('/health', (_request, response) => {
    response.json({
        status: cache.isReady && mongoose_1.default.connection.readyState === 1 ? 'ok' : 'degraded',
        service: 'app-data',
        cache: cache.isReady,
        mongodb: mongoose_1.default.connection.readyState === 1,
    });
});
app.post('/api/internal/messages', async (request, response) => {
    const message = validateMessage(request.body);
    if (!message) {
        response.status(400).json({ error: 'invalid_message' });
        return;
    }
    try {
        await Message.replaceOne({ id: message.id }, message, { upsert: true }).exec();
        await cache.setEx(cacheKey(message.id), cacheTtl, JSON.stringify(message));
        response.status(201).json({ success: true, messageId: message.id });
    }
    catch (error) {
        console.error('[app-data] persist failure', error);
        response.status(500).json({ error: 'persist_failed' });
    }
});
app.get('/api/messages/:id', async (request, response) => {
    try {
        const cached = await cache.get(cacheKey(request.params.id));
        if (cached) {
            response.json(JSON.parse(cached));
            return;
        }
        const document = await Message.findOne({ id: request.params.id }).lean().exec();
        if (!document) {
            response.status(404).json({ error: 'message_not_found' });
            return;
        }
        const message = {
            id: document.id,
            seenBy: document.seenBy,
            archived: document.archived,
            createdAt: document.createdAt,
            content: document.content,
        };
        await cache.setEx(cacheKey(message.id), cacheTtl, JSON.stringify(message));
        response.json(message);
    }
    catch (error) {
        console.error('[app-data] read failure', error);
        response.status(500).json({ error: 'read_failed' });
    }
});
async function start() {
    await Promise.all([cache.connect(), mongoose_1.default.connect(mongoUrl)]);
    app.listen(port, () => console.log(`[app-data] listening on ${port}`));
}
async function shutdown() {
    await Promise.allSettled([
        cache.isOpen ? cache.quit() : Promise.resolve(),
        mongoose_1.default.disconnect(),
    ]);
    process.exit(0);
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
start().catch((error) => {
    console.error('[app-data] startup failed', error);
    process.exit(1);
});
