import { execSync } from 'child_process';
import { writeFileSync } from 'fs';

try {
  const output = execSync('npx tsc --noEmit 2>&1', { 
    cwd: 'C:\\Users\\LENOVO\\Desktop\\master\\ResearchOS\\frontend',
    timeout: 120000 
  });
  writeFileSync('C:\\Users\\LENOVO\\Desktop\\master\\ResearchOS\\frontend\\ts_check.txt', 
    'TypeScript: 0 errors\n' + output.toString());
} catch (err: any) {
  writeFileSync('C:\\Users\\LENOVO\\Desktop\\master\\ResearchOS\\frontend\\ts_check.txt',
    err.stdout ? err.stdout.toString() : 'Error running tsc');
}
