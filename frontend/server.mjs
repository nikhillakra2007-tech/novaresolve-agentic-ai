import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { join, extname, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const port = Number(process.env.PORT || 3000);

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8'
};

const server = http.createServer(async (request, response) => {
  try {
    const parsedUrl = new URL(request.url, 'http://localhost');
    let pathname = decodeURIComponent(parsedUrl.pathname);

    // Reverse proxy API requests to backend on port 8000
    if (pathname.startsWith('/api/')) {
      const proxyHeaders = { ...request.headers, host: '127.0.0.1:8000' };
      const proxyReq = http.request(
        {
          host: '127.0.0.1',
          port: 8000,
          path: request.url,
          method: request.method,
          headers: proxyHeaders,
        },
        (proxyRes) => {
          response.writeHead(proxyRes.statusCode, proxyRes.headers);
          proxyRes.pipe(response);
        }
      );
      proxyReq.on('error', (err) => {
        response.writeHead(502, { 'Content-Type': 'application/json' });
        response.end(JSON.stringify({ error: 'Bad Gateway', message: err.message }));
      });
      request.pipe(proxyReq);
      return;
    }

    if (pathname === '/' || pathname === '') {
      pathname = '/index.html';
    }

    // Prevent path traversal
    const safePath = normalize(pathname).replace(/^(\.\.[\/\\])+/, '');
    const filePath = join(__dirname, safePath);

    const fileStat = await stat(filePath).catch(() => null);
    if (!fileStat || !fileStat.isFile()) {
      response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      response.end('Not Found');
      return;
    }

    const ext = extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    const contents = await readFile(filePath);

    response.writeHead(200, {
      'Content-Type': contentType,
      'Cache-Control': 'no-store, no-cache, must-revalidate',
      'Content-Length': Buffer.byteLength(contents)
    });
    response.end(contents);
  } catch (error) {
    response.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Internal Server Error');
  }
});

server.listen(port, '127.0.0.1', () => {
  console.log(`NovaResolve is ready at http://127.0.0.1:${port}`);
});
