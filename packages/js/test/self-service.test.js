import {test} from 'node:test';
import assert from 'node:assert/strict';
import {MickerBookClient} from '../src/index.js';
test('self service scopes, preview defaults and parent reply', async()=>{
  const calls=[];
  const client=new MickerBookClient({apiKey:'fixture', fetchImpl:async(url,options)=>{calls.push({url,options});return {ok:true,json:async()=>({ok:true})};}});
  await client.agents.home(); assert.match(calls.at(-1).url,/agents\/home$/);
  await client.agents.get('name/escaped'); assert.match(calls.at(-1).url,/name%2Fescaped$/);assert.equal(calls.at(-1).options.headers.Authorization,undefined);
  await client.notifications.list({unreadOnly:true});assert.match(calls.at(-1).url,/unreadOnly=true/);
  const count=calls.length;
  assert.equal((await client.agents.update({description:'hi'})).dryRun,true);assert.equal(calls.length,count);
  await client.agents.update({description:'hi'},{dryRun:false});assert.equal(calls.at(-1).options.method,'PUT');assert.equal(calls.at(-1).options.redirect,'error');
  await client.comments.create('post',{content:'reply',parentId:'parent'},{dryRun:false});assert.equal(JSON.parse(calls.at(-1).options.body).parentId,'parent');
});
