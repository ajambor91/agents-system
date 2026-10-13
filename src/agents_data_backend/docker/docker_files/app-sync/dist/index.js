"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const app = (0, express_1.default)();
const port = Number(process.env.PORT || 3002);
app.use(express_1.default.json({ limit: '1mb' }));
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
