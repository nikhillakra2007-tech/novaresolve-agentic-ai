import http from 'node:http';
import { readFile } from 'node:fs/promises';

const port = Number(process.env.PORT || 3000);
const routes = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
]);

const server = http.createServer(async (request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname;
  const route = routes.get(pathname);
  if (!route) {
    response.writeHead(404, { 'Content-Type': 'text/plain' });
    response.end('Not Found');
    return;
  }
  try {
    const contents = await readFile(new URL(route[0], import.meta.url));
    response.writeHead(200, { 'Content-Type': route[1], 'Cache-Control': 'no-store' });
    response.end(contents);
  } catch {
    response.writeHead(500, { 'Content-Type': 'text/plain' });
    response.end('Server Error');
  }
});

server.listen(port, '127.0.0.1', () => {
  console.log(`NovaResolve is ready at http://127.0.0.1:${port}`);
});
