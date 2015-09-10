var csrftoken = $.cookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function setup_upload_tree() {

}

function FilterSingleBranch(clickedNode, parentNodes) {
    // handles the edge of a single tree branch selected where each subfolder 
    // contains one folder only
    // we handle intent by checking to see if the user actually selected a folder or
    // whether fancytree filled in the blanks.
    if (!clickedNode.selected) return parentNodes;

    // edge case is that there is only one parent node and it only has one child,
    // that that one child node is selected and that the fancy tree has "filled in the blanks"
    // and selected up the stream

    if (parentNodes.length != 1) return parentNodes;

    myparent = parentNodes[0];

    // user selected it, go with it.
    if (myparent.key == clickedNode.key) return parentNodes;

    var mychildren = myparent.getChildren();

    if (mychildren.length != 1) return parentNodes;

    myparent.selected = false;
    myparent.setTitle(parent.title);

    return FilterSingleBranch(clickedNode, mychildren);
}

function loadUploadTree(selected) {

    var upload = $("#uploadFiles").fancytree("getTree");
    var root = $("#uploadFiles").fancytree("getRootNode");

    while (root.hasChildren()) {
        child = root.getFirstChild();
        child.remove();
    }

    //instNode.addChildren(selected);
    var fileList = [];

    selected.forEach(function (node) {
        fileList.push(node.key);
    });

    var pkt = JSON.stringify(fileList);

    //if (fileList.length > 0) {
    if (true) {
        var posted = { packet: pkt };
        $.post("/getBundle/", posted,
            function (data) {
                //alert('success');
                root.addChildren(data);

                // update bundle size
                var message = data[0]["data"];
                $("#message").text(message);
            })
            .fail(function (xhr, textStatus, errorThrown ) {
                errtext = 'data:text/html;base64,' + window.btoa(xhr.responseText);
                window.open(errtext, '_self');
            });
    }

    root.setExpanded(true);
}

$(function () {
    $.ajaxSetup({
        cache: false,
         beforeSend: function(xhr, settings) {
             function getCookie(name) {
                 var cookieValue = null;
                 if (document.cookie && document.cookie != '') {
                     var cookies = document.cookie.split(';');
                     for (var i = 0; i < cookies.length; i++) {
                         var cookie = jQuery.trim(cookies[i]);
                         // Does this cookie string begin with the name we want?
                         if (cookie.substring(0, name.length + 1) == (name + '=')) {
                             cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                             // break;
                         }
                     }
                 }
                 return cookieValue;
             }
             if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                 // Only send the token to relative URLs i.e. locally.
                 xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
             }
         } 
    });

    $('select').select2({width:'resolve'});
    $('#instrument').prop('disabled', true);

    // Create the tree inside the <div id="tree"> element.
    // Create the tree inside the <div id="tree"> element.
    $("#tree").fancytree({
        //      extensions: ["select"],
        checkbox: true,
        selectMode: 3,
        lazyLoad: function (event, data) {
            var node = data.node;
            // Load child nodes via ajax GET /getTreeData?mode=children&parent=1234
            data.result = {
                url: "/getChildren",
                data: { mode: "children", parent: node.key },
                cache: false
            };
        },

        select: function (event, data) {
            node = data.node;
            var tree = $("#tree").fancytree("getTree");
            var selected = tree.getSelectedNodes(stopOnParents = true);

            // fix selections upstream
            for (var i = 0; i < selected.length; i++) {
                selected[i].fixSelection3AfterClick();
            }

            // refresh selections
            selected = tree.getSelectedNodes(stopOnParents = true);

            // filter single branch scenario
            var filtered = FilterSingleBranch(node, selected);

            loadUploadTree(filtered);
        },

        loadChildren: function (event, data) {
            // Apply parent's state to new child nodes:
            data.node.fixSelection3AfterClick();
        }
    });

    $("#uploadFiles").fancytree({
        //      extensions: ["select"],
        checkbox: false,
        selectMode: 1
    });

    $.fn.serializeFormJSON = function () {
        var o = {};
        var a = this.serializeArray();
        $.each(a, function () {
            this.value = this.value.trim();
            if (o[this.name] !== undefined) {
                if (!o[this.name].push) {
                    o[this.name] = [o[this.name]];
                }
                o[this.name].push(this.value || '');
            } else {
                o[this.name] = this.value || '';
            }
        }
        );
        return o;
    };

    $("form").submit(function (event) {
        event.preventDefault();

        var tree = $("#tree").fancytree("getTree");
        var selected = tree.getSelectedNodes();
        var fileList = [];

        selected.forEach(function (node) {
            fileList.push(node.key);
        });

        var frm = $("form").serializeFormJSON();

        var pkt = { form: frm, files: fileList };

        $.post("/upload/", { packet: JSON.stringify(pkt) },
            function (data) {
                //alert('success');
                window.location.href = "/showStatus";
            });
    });

    $('#proposal').change(function () {
        // get selected proposal
        var p = $("#proposal").val();
        prop = { proposal: p };

        var posting = $.post("/propUser/", prop,
        function (data) {
            $("#proposal_user").empty();
            $("#proposal_user").val('')
            $('#proposal_user').select2('data', null);
            $("#proposal_user").select2({
                allowClear: true,
                data: data
            });
        })
        .fail(function (xhr, textStatus, errorThrown) {
            errtext = 'data:text/html;base64,' + window.btoa(xhr.responseText);
            window.open(errtext, '_self');
        });

        var tree = $("#tree").fancytree("getTree");
        var selected = tree.getSelectedNodes(stopOnParents = true);

        loadUploadTree(selected);

    });


});

