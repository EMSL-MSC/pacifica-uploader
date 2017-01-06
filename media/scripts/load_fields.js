
    var respondToSelect = true;

    //$(document).ready(function () {

    //    // Function code here.

    //});

    function initializeFields() {

        // populate session data before showing the status page
        var t = new Date()
        $.post("/initializeFields/", "{}",
            function (data) {
                updateFields(data);
                console.log("yay");
            })
        .fail(function (xhr, textStatus, errorThrown) {
            errtext = 'data:text/html;base64,' + window.btoa(xhr.responseText);
            window.open(errtext, '_self');
        });
    }

    function updateFields(list)
    {
        for (var i = 0; i < list.length; i++) {
            var item = list[i];
            var id = item.meta_id;
            var data = item.selection_list;

            updateField(id, data);
        }
    }

    function updateField(fieldID, data) {

        var select = "#" + fieldID;
        $(select).empty();
        $(select).val('')

        var s2 = $(select).data('select2');
        if (s2) {
            $(select).select2('data', null);
            $(select).select2({
                allowClear: true,
                data: data
            });
        }
        else {
            $(select).text(data[0].text)
        }
    }
