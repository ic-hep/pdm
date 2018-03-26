// All javascript functions related to listing files and directories


// displays page content once page is ready
function makepage() {
    // this is currently a dummy
} // makepage



function time_converter(UNIX_timestamp){
    var a = new Date(UNIX_timestamp * 1000);
    var short_time = a.toTimeString().slice(0,-18); 
    return a.toDateString() + " " + short_time;
}


function update_dir(sitenumber, dir_name) {
    var base_path = $("#pathatsite"+sitenumber).val();
    var new_path = base_path+"/"+dir_name;
    $("#pathatsite"+sitenumber).val(new_path);
    
}


// DATATABLES
class Listings {

    constructor(sitenumber) {
	this.sitenumber = sitenumber;
	// console.log(this.sitenumber);
	this.jobid = undefined;
    }

    get_query_result(){
	var sitenumber = this.sitenumber; // to stop it disappering during call back
	
	var sitename = encodeURIComponent($("#Endpoints"+sitenumber).val());
	var sitepath = encodeURIComponent($("#pathatsite"+sitenumber).val());
	console.log("Starting listing for site "+sitenumber+" and path: "+sitepath);
	
	var fullpath = "/web/js/list?siteid="+sitename+"&sitepath="+sitepath;
	// make spinner visible
	$("#listspinner"+sitenumber).show();
	$.ajax({url: fullpath, 
		success: $.proxy(this.job_submission_complete, this), 
		error: $.proxy(this.job_submission_failed, this)
	       } // dict
	      ); // ajax
    } // get_query_result

    // assuming success.....
    job_submission_complete(result) {
        // $("#listspinner"+this.sitenumber).hide();
        $("#jobnumberfield"+this.sitenumber).val(result);
	this.jobid = result;
	console.log("Listing jobid: "+this.jobid);
	setTimeout($.proxy(this.get_query_status, this), 3000);
    }

    job_submission_failed(xhr, status, err) {
        $("#listspinner"+this.sitenumber).hide();
        this.jobid = undefined;
	console.log("Listing job submission failed: "+err);
	// xhr = holds all information
        // status (text_status) = human readable error
        // err = thrown err                                                                
    } // error       


    // gets the status of the request and if it is DONE or FAILED displays the result
    get_query_status(){
	console.log("get_query_status called");
	// var j = encodeURIComponent($("#jobnumberfield"+this.sitenumber).val());
	var fullpath = "/web/js/status?jobid="+this.jobid;
	$.ajax({url: fullpath, 
		success: $.proxy(this.job_status_success, this), 
		error: $.proxy(this.job_status_failed, this)});
    } // get_query_status

    job_status_failed(xhr, status, err) {
        $("#listspinner"+this.sitenumber).hide();
        this.jobid = undefined;
        console.log("Listing job status failed: "+err);
    } // error           
    

    // TODO: Deal with 'FAILED' and all other states beyong 'DONE' correctly.
    // TODO: convert day stamp
    // TODO: make sortable by date
    // TODO: start new query when clicking on dir
    job_status_success(result) {
        var jobobj = JSON.parse(result);
	console.log("Got status: "+jobobj.status);
	// Found something ? Display if in a table
	if (jobobj.status == "DONE") {
	    $("#listspinner"+this.sitenumber).hide();
	    // make a table
	    var n_of_rows = jobobj.listing.length;
	    // TODO: apparently html5 doesn't do borders and needs a css instead
	    var table_body = '<table id="table'+this.sitenumber+'" class="display"><thead><tr><th> permissions </th> <th> uid </th> <th> gid </th> <th> size </th> <th> date </th> <th> file name </th></thead><tbody>';
	    for (var i =0; i < n_of_rows; i++) {
		table_body += '<tr>';
		table_body += '<td>';
		table_body += jobobj.listing[i]['permissions'];
		table_body +='</td><td>';
		table_body += jobobj.listing[i]['userid'];
		table_body +='</td><td>';
		table_body += jobobj.listing[i]['groupid'];
		table_body +='</td><td>';
		table_body += jobobj.listing[i]['size'];
		table_body +='</td><td>';
		// convert back from unix timestamp
		var prettytime = time_converter(jobobj.listing[i]['datestamp']);
		// table_body += jobobj.listing[i]['datestamp'];
		table_body += prettytime;
		table_body +='</td><td>';
		if (jobobj.listing[i]['is_directory'] == true) { 
		    var dir_name = jobobj.listing[i]['name']; 
		    table_body += '<a href="javascript:update_dir('+this.sitenumber+',\''+dir_name+'\');">' ;
		    table_body += dir_name;
		    table_body += '</a>';
		}
		else {
		    table_body += jobobj.listing[i]['name'];
		}
		table_body +='</td></tr>';
	    }
	    table_body+='</tbody></table>';
	    $('#tableDiv'+this.sitenumber).html(table_body);
	    $('#table'+this.sitenumber).DataTable({
		paging : false,
		searching: false,
		
	    });
        } // DONE
	else if (jobobj.status == "FAILED") {
	    $("#listspinner"+this.sitenumber).hide();
	}
	else {
	    console.log("rescheduling");
	    setTimeout($.proxy(this.get_query_status, this), 3000);
	}
	$("#reqstatus"+this.sitenumber).html(jobobj.status);
    
    } // get_status

};
