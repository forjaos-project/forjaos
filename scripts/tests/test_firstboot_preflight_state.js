#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../..');
const statePath = path.join(root, 'image/firstboot/PreflightState.js');
const qmlPath = path.join(root, 'image/firstboot/Preflight.qml');

assert.ok(fs.existsSync(statePath), 'preflight state module must exist');
const state = {};
vm.runInNewContext(fs.readFileSync(statePath, 'utf8'), state, { filename: statePath });

assert.equal(typeof state.statusLabel, 'function', 'state module must expose statusLabel');
assert.equal(typeof state.stateNote, 'function', 'state module must expose stateNote');

const status = ['Ativado', 'Desativado', 'Estado indisponível'];
assert.equal(state.statusLabel('yes', ...status), 'Ativado');
assert.equal(state.statusLabel('no', ...status), 'Desativado');
assert.equal(state.statusLabel('unknown', ...status), 'Estado indisponível');
assert.equal(state.statusLabel('unexpected', ...status), 'Estado indisponível');

const windows = ['Windows encontrado', 'Nenhum Windows detectado', 'Estado indisponível'];
assert.equal(state.statusLabel('yes', ...windows), 'Windows encontrado');
assert.equal(state.statusLabel('no', ...windows), 'Nenhum Windows detectado');
assert.equal(state.statusLabel('unknown', ...windows), 'Estado indisponível');

assert.equal(
  state.stateNote(true, true),
  'A detecção de sistema ainda não está conectada para todos os estados. Estados sem leitura aparecem como indisponíveis. Nenhuma alteração de disco ou de firmware será feita nesta tela.'
);
assert.equal(
  state.stateNote(false, true),
  'Os estados acima foram lidos deste sistema. Nenhuma alteração de disco ou de firmware será feita nesta tela.'
);
assert.equal(
  state.stateNote(true, false),
  'System detection is not connected for every status yet. Unreadable states remain marked as unavailable. This screen will not change disks or firmware.'
);
assert.equal(
  state.stateNote(false, false),
  'The statuses above were read from this system. This screen will not change disks or firmware.'
);

const qml = fs.readFileSync(qmlPath, 'utf8');
assert.match(qml, /import\s+"PreflightState\.js"\s+as\s+PreflightState/);
assert.match(qml, /PreflightState\.statusLabel\(window\.windowsState/);
assert.match(qml, /PreflightState\.statusLabel\(window\.secureBootState/);
assert.match(qml, /PreflightState\.statusLabel\(window\.mokState/);
assert.match(qml, /PreflightState\.stateNote\(window\.hasUnavailableStatus,\s*window\.portuguese\)/);
assert.match(qml, /onClicked:\s*window\.continueRequested\(\)/);

console.log('preflight state behavior tests passed');
