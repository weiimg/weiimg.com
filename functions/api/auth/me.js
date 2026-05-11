/**
 * GET /api/auth/me
 *
 * weiimg.com 端的身份驗證端點。
 * 讀取由 review.weiimg.com 簽發、設為 Domain=.weiimg.com 範圍的 auth_token cookie，
 * 驗證 JWT 並回傳使用者基本資料。
 *
 * 200 — 已登入
 * 401 — 未登入或 token 失效（前端應導向 review.weiimg.com 登入頁）
 */

import { requireAuth } from '../../_utils/auth.js';

export async function onRequestGet(context) {
    const { user, errorResponse } = await requireAuth(context);
    if (errorResponse) return errorResponse;

    return new Response(
        JSON.stringify({
            id:    user.sub,
            email: user.email,
            name:  user.name,
            role:  user.role,
        }),
        {
            status:  200,
            headers: { 'Content-Type': 'application/json' },
        }
    );
}
