// All javascript functions related to listing files and directories


$(document).ready(makepage());


function makepage() {
    $("#listbutton").click(function(){
        var sitename = encodeURIComponent($("#Endpoints").val());
        var sitepath = encodeURIComponent($("#pathatsite").val());
        var fullpath = "/web/js/list?siteid="+sitename+"&sitepath="+sitepath;
        $.ajax({url: fullpath, success: function(result) {
            $("#jobnumberfield").val(result);
        }});
    }); // click

    $("#checkbutton").click(function(){
        var j = encodeURIComponent($("#jobnumberfield").val());
        getstatus(j);
    });
} // makepage

function getstatus(jobid) {
    var fullpath = "/web/js/status?jobid="+jobid;
    $.ajax({url: fullpath, success: function(result) {
        alert(result);
        // this is a javascript object
        var jobobj = JSON.parse(result);
        // make a table
        var n_of_rows = jobobj.listings.length;
        // TODO: apparently html5 doesn't do borders and needs a css instead
        var table_body = '<table id="table1"><thead><tr><th> permissions </th> <th> nlinks </th><th> userid </th> <th> groupi\
d </th> <th> size </th> <th> date </th> <th> file name </th></thead><tbody>';
        for (i =0; i < n_of_rows; i++) {
            table_body += '<tr>';
            table_body += '<td>';
            table_body += jobobj.listings[i]['permissions'];
            table_body +='</td><td>';
            table_body += jobobj.listings[i]['nlinks'];
            table_body +='</td><td>';
            table_body += jobobj.listings[i]['userid'];
            table_body +='</td><td>';
            table_body += jobobj.listings[i]['groupid'];
            table_body +='</td><td>';
            table_body += jobobj.listings[i]['size'];
            table_body +='</td><td>';
            table_body += jobobj.listings[i]['datestamp'];
            table_body +='</td><td>';
	    if (jobobj.listings[i]['is_directory'] == true) { table_body += '<font color="blue">';}
	    table_body += jobobj.listings[i]['name'];
            if (jobobj.listings[i]['is_directory'] == true) { table_body += '</font>';}
            table_body +='</td></tr>';
        }
        table_body+='</tbody></table>';
        $('#tableDiv').html(table_body);
        $("#theend").html(jobobj.status);
    }});
}
