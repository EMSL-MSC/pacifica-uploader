var csrftoken = $.cookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function setup_upload_tree() {

}

$(function () {
    $.ajaxSetup({
        cache: false,
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    $('select').select2();

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
            var node = data.node;
            var tree = $("#tree").fancytree("getTree");
            var selected = tree.getSelectedNodes(stopOnParents = true);

            var upload = $("#uploadFiles").fancytree("getTree");
            var root = $("#uploadFiles").fancytree("getRootNode");



            while (root.hasChildren()) {
                child = root.getFirstChild();
                child.remove();
            }

            var propNode = root.addChildren({
                title: "Proposal", id: "Proposal", expand: true,
                folder: true
            });
            instNode = propNode.addChildren({
                title: "Instrument", id: "Instrument", expand: true,
                folder: true
            });

            instNode.addChildren(selected);

            root.setExpanded(true);
            propNode.setExpanded(true);
            instNode.setExpanded(true);
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

    jQuery["postJSON"] = function (url, data, callback) {
        // shift arguments if data argument was omitted
        if (jQuery.isFunction(data)) {
            callback = data;
            data = undefined;
        }

        return jQuery.ajax({
            url: url,
            type: "POST",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify(data),
            success: callback
        });
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
                window.location.replace("/showStatus");
            });
    });



    // setup change notification on the proposal picker
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
        .fail(function () {
            alert("error");
        });
    });
});

