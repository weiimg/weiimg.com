/**
 * JWT 工具模組
 *
 * 與 review.weiimg.com (video-review-platform) 共用同一份實作。
 * 兩邊必須使用相同的 JWT_SECRET 才能互相驗證 token。
 *
 * 使用 Web Crypto API（Cloudflare Workers 原生支援）實作 HMAC-SHA256 簽名與驗證。
 */

function stringToBase64url(str) {
    return btoa(unescape(encodeURIComponent(str)))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
}

function bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (const byte of bytes) {
        binary += String.fromCharCode(byte);
    }
    return btoa(binary)
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
}

function base64urlToString(str) {
    const padded = str + '='.repeat((4 - (str.length % 4)) % 4);
    const base64 = padded.replace(/-/g, '+').replace(/_/g, '/');
    try {
        return decodeURIComponent(escape(atob(base64)));
    } catch {
        throw new Error('Base64URL 解碼失敗，token 格式可能已損毀');
    }
}

function base64urlToBuffer(str) {
    const padded = str + '='.repeat((4 - (str.length % 4)) % 4);
    const base64 = padded.replace(/-/g, '+').replace(/_/g, '/');
    const binary = atob(base64);
    const buffer = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        buffer[i] = binary.charCodeAt(i);
    }
    return buffer;
}

export async function signJWT(payload, secret, expiresIn) {
    const now = Math.floor(Date.now() / 1000);
    const header = { alg: 'HS256', typ: 'JWT' };
    const fullPayload = {
        ...payload,
        iat: now,
        exp: now + Number(expiresIn),
    };

    const headerEncoded  = stringToBase64url(JSON.stringify(header));
    const payloadEncoded = stringToBase64url(JSON.stringify(fullPayload));
    const signingInput   = `${headerEncoded}.${payloadEncoded}`;

    const cryptoKey = await crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode(secret),
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign']
    );

    const signatureBuffer  = await crypto.subtle.sign(
        'HMAC',
        cryptoKey,
        new TextEncoder().encode(signingInput)
    );

    const signatureEncoded = bufferToBase64url(signatureBuffer);
    return `${signingInput}.${signatureEncoded}`;
}

export async function verifyJWT(token, secret) {
    try {
        const parts = token.split('.');
        if (parts.length !== 3) return null;

        const [headerEncoded, payloadEncoded, signatureEncoded] = parts;
        const signingInput = `${headerEncoded}.${payloadEncoded}`;

        const cryptoKey = await crypto.subtle.importKey(
            'raw',
            new TextEncoder().encode(secret),
            { name: 'HMAC', hash: 'SHA-256' },
            false,
            ['verify']
        );

        const isValid = await crypto.subtle.verify(
            'HMAC',
            cryptoKey,
            base64urlToBuffer(signatureEncoded),
            new TextEncoder().encode(signingInput)
        );

        if (!isValid) return null;

        const payload = JSON.parse(base64urlToString(payloadEncoded));

        const now = Math.floor(Date.now() / 1000);
        if (payload.exp && payload.exp < now) return null;

        return payload;
    } catch {
        return null;
    }
}
