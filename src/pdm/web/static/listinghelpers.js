// My first javascript
// All javascript functions related to listing files and directories
/*jshint sub:true*/
/*jshint esversion: 6*/

function time_converter(UNIX_timestamp) {
    "use strict";
    var a = new Date(UNIX_timestamp * 1000);
    var short_time = a.toTimeString().slice(0, -18);
    var short_date = a.toDateString().slice(3);
    return short_date + " " + short_time;
}


// DATATABLES
class Listings {

    constructor(sitenumber) {
	this.sitenumber = sitenumber;
	// console.log(this.sitenumber);
	this.jobid = undefined;
    }

    // updates the directory entry in the list field
    update_dir(dir_name) {
	"use strict";
	var base_path = $("#pathatsite" + this.sitenumber).val();
	var new_path = base_path + "/" + dir_name;
	// replace any double slashes
	var clean_new_path = new_path.replace(/\/\//g, "/");
	$("#pathatsite" + this.sitenumber).val(clean_new_path);
    }



    // and actually lists the new directory
    update_and_list_dir(dir_name) {
	"use strict";
	this.update_dir(dir_name);
	console.log('update_and_list_dir');
	this.get_query_result();
    }




    // this is called by the 'List' button
    get_query_result(){
	var sitenumber = this.sitenumber; // to stop it disappering during call back
	
	var sitename = encodeURIComponent($("#Endpoints" + sitenumber).val());
	var sitepath = encodeURIComponent($("#pathatsite" + sitenumber).val());
	if (sitename == "droptitle") {
	    return $('#tableDiv'+this.sitenumber).html("<b>Please choose a site !</b>");
	}
	console.log("Starting listing for site "+sitenumber+" and path: "+sitepath);
	console.log("Chose site name: "+sitename);
	var fullpath = "/web/js/list?siteid="+sitename+"&sitepath="+sitepath;
	// make spinner visible
	$("#listspinner"+sitenumber).show();
	$('#tableDiv'+this.sitenumber).html("");

	$.ajax({url: fullpath, 
		success: $.proxy(this.job_submission_complete, this), 
		error: $.proxy(this.job_submission_failed, this)
	       } // dict
	      ); // ajax
    } // get_query_result

    // assuming success.....
    job_submission_complete(result) {
        $("#jobnumberfield"+this.sitenumber).val(result);
	this.jobid = result;
	this.jobattempts = 10; 
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


    go_up_one() {
	var sitepath = encodeURIComponent($("#pathatsite" + this.sitenumber).val());
	var up_path = this.which_way_is_up(sitepath);
	$("#pathatsite" + this.sitenumber).val(up_path);
        this.get_query_result();
    }	

    which_way_is_up(path_uri) {
	var one_dir_up = '/';
	// make this fit unix style again
	var path = decodeURIComponent(path_uri);
	// remove trailing slash(es) if present, thank you stackoverflow
	var clean_path = path.replace(/\/+$/, "");
	// remove any double slashes, thank you Simon
	clean_path = clean_path.replace(/\/\/+/g,"/");
	// deal with '/'
	if (clean_path == '') { clean_path = '/';}
	// all the special cases
	if ( (clean_path == '/') || (clean_path == '/~') || (clean_path == '~')) { 
	    return one_dir_up; 
	}
	else {
	    // remove everything until the next slash, but leave / (i.e. /bin -> /, /bin/blah -> /bin/)
	    var dir_name_bits = clean_path.split("/");
	    one_dir_up = dir_name_bits.slice(0, dir_name_bits.length - 1).join("/");
	    if (one_dir_up == "") { one_dir_up = '/'; } 
	}
	console.log(one_dir_up);
	return one_dir_up;
    } // which_way_is_up
    

    job_status_success(result) {
        var jobobj = JSON.parse(result);
	console.log("Got status: "+jobobj.status);
	// Found something ? Display if in a table
	if (jobobj.status == "DONE") {
	    $("#listspinner"+this.sitenumber).hide();
	    // make the navigation bar visible
	    $("#navbar"+this.sitenumber).show();
	    // make a table
	    var n_of_rows = jobobj.listing.length;
	    var table_body = '<table id="table'+this.sitenumber+'" class="display"><thead><tr><th>type </th> <th> uid </th> <th> gid </th> <th> size </th> <th> date </th> <th> file name </th></thead><tbody>';
	    var sitepath = encodeURIComponent($("#pathatsite" + this.sitenumber).val());

	    for (var i =0; i < n_of_rows; i++) {
		table_body += '<tr>';
		table_body += '<td>';
		if (jobobj.listing[i]['is_directory'] == true) {
		    table_body += '<img src = "/static/images/folder'+this.sitenumber+'.png">'; 
		}
		else {
		    table_body += '<img src = "/static/images/file'+this.sitenumber+'.png">';
		}
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
		    table_body += '<a href="javascript:list'+this.sitenumber+'.update_and_list_dir(\''+dir_name+'\');">' ;
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
		info: false,
		"order": [[ 5, "asc" ]]
	    });
        } // DONE
	else if (jobobj.status == "FAILED") {
	    $("#listspinner"+this.sitenumber).hide();
	    $("#navbar"+this.sitenumber).hide();
	}
	else {
	    console.log("rescheduling");
	    if (this.jobattempts > 0) {
		this.jobattempts--;
		setTimeout($.proxy(this.get_query_status, this), 3000);
	    }
	    else {
		$("#listspinner"+this.sitenumber).hide();
		$("#reqstatus"+this.sitenumber).html("STUCK");
		return;
	    }
	}
	if (jobobj.status == "FAILED") {
	    var failed_string = '<p style="color:red">FAILED</>'
	    $("#reqstatus"+this.sitenumber).html(failed_string);
	}
	else {
	    $("#reqstatus"+this.sitenumber).html(jobobj.status);
	}
    
    } // get_status
} // Listings
