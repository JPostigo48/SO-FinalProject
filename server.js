import express from 'express';
import expressLayouts from "express-ejs-layouts";

import path, { join } from 'path';
import { fileURLToPath } from "url";
import { spawn } from 'child_process';
import bp from 'body-parser';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

app.set('views', join(__dirname, 'views'));
app.set('view engine', 'ejs');
app.use(expressLayouts);
app.set("layout", "layout");

app.use(express.static(join(__dirname, 'public')));
app.use(bp.urlencoded({ extended: true }));

app.get('/', (req, res) => {
  res.render('index', { error: null });
});

app.post('/simulate', (req, res) => {
  const numProcs = parseInt(req.body.numProcs, 10);
  let quantum = req.body.quantum ? parseInt(req.body.quantum, 10) : 10;
  if (!numProcs || numProcs <= 0) {
    return res.render('index', { error: 'La cantidad de procesos debe ser un número positivo.' });
  }
  if (!quantum || quantum <= 0) {
    quantum = 10;
  }
  const pythonPath = join(__dirname, 'python', 'simulate.py');
  const args = [pythonPath, numProcs.toString(), quantum.toString()];
  const pythonProcess = spawn('python3', args);
  let output = '';
  let errorOutput = '';
  pythonProcess.stdout.on('data', (data) => {
    output += data.toString();
  });
  pythonProcess.stderr.on('data', (data) => {
    errorOutput += data.toString();
  });
  pythonProcess.on('close', (code) => {
    if (code !== 0 || errorOutput) {
      console.error('Error ejecutando el script Python:', errorOutput);
      return res.render('index', { error: 'Error al ejecutar la simulación. Consulte los logs del servidor.' });
    }
    try {
      const result = JSON.parse(output);
      res.render('results', {
        data: result,
        quantum: quantum,
      });
    } catch (err) {
      console.error('Error analizando el JSON:', err);
      return res.render('index', { error: 'Error al procesar la salida de la simulación.' });
    }
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor escuchando en http://localhost:${PORT}`);
});