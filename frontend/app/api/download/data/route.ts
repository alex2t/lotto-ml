/**
 * The admin data bundle: data/*.json, data/analysis/* and data/irish500.csv, streamed as a zip.
 *
 * This route is the one place in frontend/ that reads irish500.csv - the owner retrieving
 * their own input file, not the site displaying it (F-35). Streamed, never buffered: the
 * JSON alone is about 5 MB.
 */
import { ZipArchive } from 'archiver';
import fs from 'node:fs';
import path from 'node:path';
import { Readable } from 'node:stream';
import { dataDir } from '@/lib/data/artifacts';
import { latestDrawDate } from '@/lib/data/schedule';

export const runtime = 'nodejs';

export async function GET() {
  const dir = dataDir();
  const archive = new ZipArchive({ zlib: { level: 9 } });

  archive.glob('*.json', { cwd: dir });
  const analysis = path.join(dir, 'analysis');
  if (fs.existsSync(analysis)) archive.directory(analysis, 'analysis');
  archive.file(path.join(dir, 'irish500.csv'), { name: 'irish500.csv' });

  const fileName = `lotto-data-${latestDrawDate()}.zip`;
  archive.finalize();

  return new Response(Readable.toWeb(archive) as ReadableStream, {
    headers: {
      'Content-Type': 'application/zip',
      'Content-Disposition': `attachment; filename="${fileName}"`,
      'Cache-Control': 'no-store',
    },
  });
}
