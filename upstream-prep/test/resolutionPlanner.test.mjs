import test from 'node:test';
import assert from 'node:assert/strict';
import { buildCitationPlan } from '../src/resolutionPlanner.mjs';

const item = { library: 'user', itemKey: 'ABCDEFGH', title: 'Test source', doi: '10.1000/test' };
function resolver({alias='found',doi='found',zotero='found'}={}) {
  const calls=[];
  return { calls,
    async resolveAlias(x){calls.push('alias:'+x);return {status:alias,item}},
    async resolveDOI(x){calls.push('doi:'+x);return {status:doi,item}},
    async resolveZoteroItem(x){calls.push('zotero:'+x.key);return {status:zotero,item}},
  };
}
test('same alias resolved once across multiple paragraphs', async()=>{
  const r=resolver(); const p=await buildCitationPlan('A [[Z:06937]].\nB [[Z:06937]].',r);
  assert.equal(p.counts.RESOLVED,2);assert.equal(p.uniqueSources.length,1);
  assert.deepEqual(r.calls,['alias:06937']);
  assert.ok(p.replacements[0].start > p.replacements[1].start);
});
test('failure does not convert other markers', async()=>{
  const r=resolver({doi:'missing'}); const p=await buildCitationPlan('[[Z:06937]] [[ZDOI:10.1000/test]]',r);
  assert.equal(p.replacements.length,1);assert.equal(p.counts.MISSING,1);assert.equal(p.hasErrors,true);
});
test('ambiguous sources must remain unresolved', async()=>{
  const p=await buildCitationPlan('[[Z:0001]]',resolver({alias:'ambiguous'}));
  assert.equal(p.counts.AMBIGUOUS,1);assert.equal(p.replacements.length,0);
});
test('unknown legacy alias remains unresolved', async()=>{
  const p=await buildCitationPlan('[[Z:0001]]',{resolveAlias:async()=>({status:'missing'})});
  assert.equal(p.counts.MISSING,1);
});
test('invalid markers are never sent to external resolver', async()=>{
  const r=resolver();const p=await buildCitationPlan('[[Z:abc]] [[Z:06937]]',r);
  assert.equal(p.counts.INVALID,1);assert.deepEqual(r.calls,['alias:06937']);
});
test('lookup error is contained and logged', async()=>{
  const r={resolveAlias:async()=>{throw Error('temporary outage')}};
  const p=await buildCitationPlan('[[Z:100]]',r);
  assert.equal(p.counts.ERROR,1);assert.match(p.occurrences[0].reason,/outage/);
});
test('invalid Zotero item identity is refused', async()=>{
  const r={resolveAlias:async()=>({status:'found',item:{library:'user',itemKey:'BAD'}})};
  const p=await buildCitationPlan('[[Z:100]]',r);
  assert.equal(p.counts.ERROR,1);assert.equal(p.replacements.length,0);
});
test('explicit group and personal library references cannot collide', async()=>{
  const r={resolveZoteroItem:async({library,key})=>({status:'found',item:{library,itemKey:key}})};
  const p=await buildCitationPlan('[[ZOTERO:user/ABCDEFGH]] [[ZOTERO:group:1/ABCDEFGH]]',r);
  assert.equal(p.uniqueSources.length,2);
});
test('an unhandled resolver status is an error', async()=>{
  const r={resolveAlias:async()=>({status:'maybe'})};
  const p=await buildCitationPlan('[[Z:100]]',r);
  assert.equal(p.counts.ERROR,1);
});
test('no mutation of original text', async()=>{
  const text='Sentence [[Z:06937]].'; await buildCitationPlan(text,resolver());
  assert.equal(text,'Sentence [[Z:06937]].');
});

test('a mismatched DOI cannot be silently converted', async()=>{
  const r={resolveDOI:async()=>({status:'found',item:{...item, doi:'10.1000/other'}})};
  const p=await buildCitationPlan('[[ZDOI:10.1000/test]]',r);
  assert.equal(p.counts.ERROR,1);assert.equal(p.replacements.length,0);
});
test('a returned item from a different library is not accepted', async()=>{
  const r={resolveZoteroItem:async()=>({status:'found',item})};
  const p=await buildCitationPlan('[[ZOTERO:group:5/ABCDEFGH]]',r);
  assert.equal(p.counts.ERROR,1);
});
