window.addEventListener("load", _=>{
	document.querySelector("#confirm-drop").onclick = _=>{
		if (document.querySelector("#drop-dialog input[name='table-structure']").checked){
			window.location.href = 'drop_table'
		} else{
			window.location.href = 'delete_table_data'
		}
	}
})
