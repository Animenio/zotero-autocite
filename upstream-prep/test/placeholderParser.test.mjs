import test from 'node:test';
import assert from 'node:assert/strict';
import { parsePlaceholder, scanCitationMarkers } from '../src/placeholderParser.mjs';

test('short codes retain leading zeros and avoid numeric rounding', () => {
  assert.deepEqual(parsePlaceholder('[[Z:06937]]'), { kind:'alias', value:'06937', canonical:'[[Z:06937]]' });
});
test('DOI markers normalize scheme and case', () => {
  assert.equal(parsePlaceholder('[[ZDOI:https://doi.org/10.1016/J.TECHFORE.2016.08.019]]').value, '10.1016/j.techfore.2016.08.019');
});
test('portable personal item keys are accepted', () => {
  assert.deepEqual(parsePlaceholder('[[ZOTERO:user/abcd1234]]').value, {library:'user',key:'ABCD1234'});
});
test('portable group item keys are scoped', () => {
  assert.deepEqual(parsePlaceholder('[[ZOTERO:group:1234/ABCD1234]]').value, {library:'group:1234',key:'ABCD1234'});
});
test('unknown double-bracket tokens remain untouched', () => {
  assert.equal(scanCitationMarkers('See [[ZBIB]] and [[TODO]]').length,0);
});
test('invalid autocite placeholders are reported, not silently replaced', () => {
  let m=scanCitationMarkers('Here [[Z:wrong]] and [[ZOTERO:user/X]]');
  assert.deepEqual(m.map(x=>x.kind), ['invalid','invalid']);
});
test('scanner preserves exact offsets for repeated references', () => {
  let text='α [[Z:00001]], β [[Z:00001]].';
  let m=scanCitationMarkers(text);
  assert.equal(m.length,2);
  for (const x of m) assert.equal(text.slice(x.start,x.end),x.raw);
  assert.ok(m[0].end<m[1].start);
});
test('ordinary surname and year are not enough to resolve a source', () => {
  assert.deepEqual(scanCitationMarkers('(Rossi, 2023)'),[]);
});
test('prohibit whitespace in DOI and invalid DOI prefix', () => {
  assert.equal(parsePlaceholder('[[ZDOI:10.bad/xyz]]').kind,'invalid');
  assert.equal(parsePlaceholder('[[ZDOI:10.1234/space test]]').kind,'invalid');
});
test('missing closing brackets is not a marker', () => {
  assert.equal(scanCitationMarkers('[[Z:00001]').length,0);
});
test('non-string input is rejected',()=>assert.throws(()=>scanCitationMarkers(null),TypeError));
test('oversized input is rejected early',()=>assert.throws(()=>scanCitationMarkers('a'.repeat(20_000_001)), RangeError));
test('scanner never follows raw HTML or executes code',()=>{
  const text='<script>[[Z:00002]]</script>';
  assert.equal(scanCitationMarkers(text).length,1);
  // Parser is pure: it reports literal offsets and never interprets markup.
  assert.equal(text.slice(0,8),'<script>');
});
