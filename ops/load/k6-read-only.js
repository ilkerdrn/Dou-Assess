import http from 'k6/http';
import { check, sleep } from 'k6';

const base = (__ENV.BASE_URL || 'http://127.0.0.1:8080').replace(/\/$/, '');
const token = __ENV.ACCESS_TOKEN || '';
const targetPath = __ENV.TARGET_PATH || '/api/programs';

export const options = {
  stages: [
    { duration: __ENV.RAMP || '30s', target: Number(__ENV.VUS || 50) },
    { duration: __ENV.HOLD || '2m', target: Number(__ENV.VUS || 50) },
    { duration: '20s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1500'],
  },
};

export function setup() {
  const r = http.get(`${base}/api/ready`);
  check(r, { 'ready 200': (x) => x.status === 200 });
}

export default function () {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const r = http.get(`${base}${targetPath}`, { headers });
  check(r, {
    'status expected': (x) => token ? x.status === 200 : [200, 401, 403].includes(x.status),
    'body returned': (x) => x.body && x.body.length > 0,
  });
  sleep(Number(__ENV.SLEEP || 1));
}
