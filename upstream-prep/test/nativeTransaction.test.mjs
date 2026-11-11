import test from 'node:test';
import assert from 'node:assert/strict';
import { buildCitationPlan } from '../src/resolutionPlanner.mjs';
import { applyNativeConversion } from '../src/nativeTransaction.mjs';

const resolved={library:'user',itemKey:'ABCDEFGH',title:'Paper'};
const resolver={resolveAlias:async()=>({status:'found',item:resolved})};
function fakeAdapter() {
  const calls=[];
  return {calls,
    async beginUndoTransaction(){calls.push('begin');return 1;},
    async replaceMarkerWithCitationField(d){calls.push(d);},
    async commitUndoTransaction(){calls.push('commit');},
    async rollbackUndoTransaction(){calls.push('rollback');},
  };
}
test('two text placeholders convert in reverse positional order',async()=>{
  const plan=await buildCitationPlan('A [[Z:00001]] B [[Z:00001]]',resolver);
  const adapter=fakeAdapter();const result=await applyNativeConversion(plan,adapter);
  assert.equal(result.applied,2);
  assert.ok(adapter.calls[1].start>adapter.calls[2].start);
  assert.deepEqual([adapter.calls[0],adapter.calls[3]],['begin','commit']);
});
test('an unresolved placeholder blocks all document edits by default',async()=>{
  const plan=await buildCitationPlan('[[Z:00001]] [[Z:00002]]',{resolveAlias:async x=>x==='00001'?{status:'found',item:resolved}:{status:'missing'}});
  const adapter=fakeAdapter();const r=await applyNativeConversion(plan,adapter);
  assert.equal(r.status,'BLOCKED_UNRESOLVED');assert.deepEqual(adapter.calls,[]);
});
test('partial conversion requires explicit opt-in',async()=>{
  const plan=await buildCitationPlan('[[Z:00001]] [[Z:00002]]',{resolveAlias:async x=>x==='00001'?{status:'found',item:resolved}:{status:'missing'}});
  const adapter=fakeAdapter();const r=await applyNativeConversion(plan,adapter,{allowPartial:true});
  assert.equal(r.applied,1);
});
test('failed insertion triggers rollback',async()=>{
  const plan=await buildCitationPlan('[[Z:00001]]',resolver);const adapter=fakeAdapter();
  adapter.replaceMarkerWithCitationField=async()=>{adapter.calls.push('fail');throw Error('COM failure')};
  await assert.rejects(()=>applyNativeConversion(plan,adapter),/COM failure/);
  assert.deepEqual(adapter.calls,['begin','fail','rollback']);
});
test('missing adapter methods fail before any edit',async()=>{
  const plan=await buildCitationPlan('[[Z:00001]]',resolver);
  await assert.rejects(()=>applyNativeConversion(plan,{}),/missing beginUndoTransaction/);
});
test('empty plan requires no adapter methods',async()=>{
  const plan=await buildCitationPlan('Plain prose.',{});
  const r=await applyNativeConversion(plan,{});
  assert.equal(r.status,'NO_CHANGES');
});
