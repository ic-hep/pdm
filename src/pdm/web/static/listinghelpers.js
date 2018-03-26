// All javascript functions related to listing files and directories


// displays page content once page is ready
function makepage() {
    // this is currently a dummy
} // makepage



function timeConverter(UNIX_timestamp){
  var a = new Date(UNIX_timestamp * 1000);
  return a.toDateString() + " " + a.toTimeString();
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
    }

    get_query_result(){
	var sitenumber = this.sitenumber; // to stop it disappering during call back
	
	var sitename = encodeURIComponent($("#Endpoints"+sitenumber).val());
	var sitepath = encodeURIComponent($("#pathatsite"+sitenumber).val());
	console.log(sitenumber);
	var fullpath = "/web/js/list?siteid="+sitename+"&sitepath="+sitepath;
	// make spinner visible
	$("#listspinner"+sitenumber).show();
	$.ajax({url: fullpath, success: function(result) {
	    $("#listspinner"+sitenumber).hide();
            $("#jobnumberfield"+sitenumber).val(result);}, 
		error: function(xhr, status, err) {
		    $("#listspinner"+sitenumber).hide();
		    alert("Failed to load listing: "+status);
		    // xhr = holds all information
		    // status (text_status) = human readable error
		    // err = thrown err
		} // error
	       } // dict
	      ); // ajax
    } // get_query_result

    // gets the status of the request and if it is DONE or FAILED displays the result
    get_query_status(){
	var j = encodeURIComponent($("#jobnumberfield"+this.sitenumber).val());
	this.get_status(j);
    } // get_query_status



    // TODO: Deal with 'FAILED' and all other states beyong 'DONE' correctly.
    // TODO: convert day stamp
    // TODO: make sortable by date
    // TODO: start new query when clicking on dir
    get_status(jobid) {
	var sitenumber = this.sitenumber; // to stop it disappering during call back  
	var fullpath = "/web/js/status?jobid="+jobid;
	$.ajax({url: fullpath, success: function(result) {
            alert(result);
            // this is a javascript object
            var jobobj = JSON.parse(result);

	    // Found something ? Display if in a table
	    if (jobobj.status == "DONE") {
		
		// make a table
		var n_of_rows = jobobj.listing.length;
		// TODO: apparently html5 doesn't do borders and needs a css instead
		var table_body = '<table id="table1"><thead><tr><th> permissions </th> <th> nlinks </th><th> userid </th> <th> groupi\ d </th> <th> size </th> <th> date </th> <th> file name </th></thead><tbody>';
		for (var i =0; i < n_of_rows; i++) {
		    table_body += '<tr>';
		    table_body += '<td>';
		    table_body += jobobj.listing[i]['permissions'];
		    table_body +='</td><td>';
		    table_body += jobobj.listing[i]['nlinks'];
		    table_body +='</td><td>';
		    table_body += jobobj.listing[i]['userid'];
		    table_body +='</td><td>';
		    table_body += jobobj.listing[i]['groupid'];
		    table_body +='</td><td>';
		    table_body += jobobj.listing[i]['size'];
		    table_body +='</td><td>';
		    // convert back from unix timestamp
		    var prettytime = timeConverter(jobobj.listing[i]['datestamp']);
		    // table_body += jobobj.listing[i]['datestamp'];
		    table_body += prettytime;
		    table_body +='</td><td>';
		    if (jobobj.listing[i]['is_directory'] == true) { 
			var dir_name = jobobj.listing[i]['name']; 
			table_body += '<a href="javascript:update_dir('+sitenumber+',\''+dir_name+'\');">' ;
			table_body += dir_name;
			table_body += '</a>';
		    }
		    else {
			table_body += jobobj.listing[i]['name'];
		    }
		    table_body +='</td></tr>';
		}
		table_body+='</tbody></table>';
		$('#tableDiv'+sitenumber).html(table_body);
            } // DONE
	    $("#reqstatus"+sitenumber).html(jobobj.status);
	}});
    } // get_status

};
