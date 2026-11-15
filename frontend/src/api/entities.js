import {api} from './client.js';
export const datasets={list:()=>api('/datasets'),get:id=>api('/datasets/'+id),create:data=>api('/datasets',{method:'POST',body:JSON.stringify(data)})};
export const jobs={list:()=>api('/jobs'),get:id=>api('/jobs/'+id),create:data=>api('/jobs',{method:'POST',body:JSON.stringify(data)}),approve:id=>api('/jobs/'+id+'/approve',{method:'POST'})};
export const reports={list:()=>api('/reports'),create:data=>api('/reports',{method:'POST',body:JSON.stringify(data)}),toggle:id=>api('/reports/'+id+'/toggle',{method:'POST'}),deliveries:()=>api('/deliveries')};
export const bills={list:()=>api('/bills'),get:id=>api('/bills/'+id),import:data=>api('/bills/import',{method:'POST',body:JSON.stringify(data)})};
export const recon={groups:status=>api('/recon/groups'+(status?'?status='+status:'')),get:id=>api('/recon/groups/'+id),create:data=>api('/recon/groups',{method:'POST',body:JSON.stringify(data)}),confirm:id=>api('/recon/groups/'+id+'/confirm',{method:'POST'}),revoke:(id,reason)=>api('/recon/groups/'+id+'/revoke',{method:'POST',body:JSON.stringify({reason:reason||''})})};
