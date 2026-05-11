/**
 * 認證中介層 — 從 HttpOnly Cookie 解析並驗證 JWT
 *
 * 與 review.weiimg.com 共用同一份實作與相同的 JWT_SECRET。
 * weiimg.com 自身不持有使用者資料庫，只負責驗證 token 是否有效。
 */

import { verifyJWT } from './jwt.js';

function parseCookies(cookieHeader) {
    const cookies = {};
    if (!cookieHeader) return cookies;

    cookieHeader.split(';').forEach(part => {
        const eqIndex = part.indexOf('=');
        if (eqIndex === -1) return;

        const key   = part.slice(0, eqIndex).trim();
        const value = part.slice(eqIndex + 1).trim();
        if (key) cookies[key] = value;
    });

    return cookies;
}

export async function getAuthUser(request, env) {
    const cookieHeader = request.headers.get('Cookie') || '';
    const cookies      = parseCookies(cookieHeader);
    const token        = cookies['auth_token'];

    if (!token) return null;

    const payload = await verifyJWT(token, env.JWT_SECRET);
    return payload;
}

export async function requireAuth(context) {
    const { request, env } = context;

    const user = await getAuthUser(request, env);

    if (!user) {
        return {
            user:          null,
            errorResponse: new Response(
                JSON.stringify({ error: '請先登入後再進行此操作' }),
                {
                    status:  401,
                    headers: { 'Content-Type': 'application/json' },
                }
            ),
        };
    }

    return { user, errorResponse: null };
}
